import time
import uuid
import asyncio
from typing import Any, Optional, Callable, Dict, List
from opentelemetry import trace
from oao.telemetry import get_tracer

from oao.runtime.state_machine import (
    StateMachine,
    AgentState,
    InvalidStateTransition,
)
from oao.policy.strict_policy import PolicyViolation
from oao.protocol.report import ExecutionReport
from oao.adapters.registry import AdapterRegistry
from oao.runtime.event_bus import EventBus
from oao.runtime.event_bus import EventBus, Event
from oao.runtime.default_logger import console_logger
from oao.runtime.events import EventType, ExecutionEvent
import oao.adapters.langchain_adapter # Ensure registration
import oao.metrics as metrics
from oao.runtime.hashing import compute_execution_hash
from oao.runtime.resilience import execute_with_retry, execute_with_retry_async, RetryConfig, BackoffStrategy
from oao.runtime.execution import Execution, ExecutionStatus
from oao.runtime.event_store import InMemoryEventStore, RedisEventStore
from oao.runtime.persistence import RedisPersistenceAdapter
from oao.adapters.base_adapter import BaseAdapter
from oao.adapters.langchain_adapter import LangChainAdapter

# Mock Adapter for testing
class MockAdapter(BaseAdapter):
    def __init__(self, agent):
        self.agent = agent
        self._token_usage = 0
    async def execute_async(self, task, context=None, policy=None):
        res = await self.agent.ainvoke(task, context=context, policy=policy)
        self._token_usage = res.get("token_usage", 0)
        return res
    def execute(self, task, context=None, policy=None):
        res = self.agent.invoke(task, context=context, policy=policy)
        self._token_usage = res.get("token_usage", 0)
        return res
    def get_token_usage(self): return self._token_usage

AdapterRegistry.register("mock", MockAdapter)

class Orchestrator:
    """
    Main runtime controller for OpenAgentOrchestrator.
    Supports both sync and async execution.
    """

    def __init__(self, persistence=None, event_store=None, policy=None):
        self.persistence = persistence or RedisPersistenceAdapter()
        self.event_store = event_store or RedisEventStore()
        self.policy = policy
        self.state_machine = StateMachine()
        self.event_bus = EventBus()
        self.context = {}
        self.current_execution_id = None
        self._simulation_hooks = {}

        # Register default event hooks
        self.event_bus.register(EventType.STATE_ENTER, console_logger)
        self.event_bus.register(EventType.POLICY_VIOLATION, console_logger)
        self.event_bus.register(EventType.EXECUTION_COMPLETED, console_logger)

        # Register global listeners
        from oao.runtime.events import GlobalEventRegistry
        for event_type in EventType:
            for listener in GlobalEventRegistry.get_listeners(event_type):
                self.event_bus.register(event_type, listener)

    # =====================================================
    # SIMULATION HOOKS
    # =====================================================
    def add_simulation_hook(self, name: str, callback: Callable):
        """Add a hook for testing and simulation."""
        self._simulation_hooks[name] = callback

    async def _execute_simulation_hook_async(self, name: str, *args, **kwargs):
        """Execute a simulation hook asynchronously."""
        if name in self._simulation_hooks:
            hook = self._simulation_hooks[name]
            if asyncio.iscoroutinefunction(hook):
                await hook(*args, **kwargs)
            else:
                hook(*args, **kwargs)

    def _execute_simulation_hook_sync(self, name: str, *args, **kwargs):
        """Execute a simulation hook synchronously. Skips async hooks."""
        if name in self._simulation_hooks:
            hook = self._simulation_hooks[name]
            if not asyncio.iscoroutinefunction(hook):
                hook(*args, **kwargs)
            else:
                print(f"[WARN] Skipping async simulation hook '{name}' in sync execution mode.")

    # =====================================================
    # TRACING HELPER
    # =====================================================
    def _create_execution_event(self, execution_id, event_type, step_number, **kwargs):
        """Helper to create ExecutionEvent with current trace context."""
        span = trace.get_current_span()
        span_ctx = span.get_span_context()
        trace_id = None
        span_id = None
        if span_ctx.is_valid:
             trace_id = format(span_ctx.trace_id, "032x")
             span_id = format(span_ctx.span_id, "016x")
        
        return ExecutionEvent(
             execution_id=execution_id,
             step_number=step_number,
             event_type=event_type,
             trace_id=trace_id,
             span_id=span_id,
             **kwargs
        )

    # =====================================================
    # SYNC EXECUTION
    # =====================================================

    def run(
        self, 
        agent: Any, 
        task: str, 
        framework: str = "langchain",
        execution_id: Optional[str] = None,
        from_step: Optional[int] = None
    ) -> ExecutionReport:

        metrics.active_agents.inc()
        
        # Create canonical Execution object
        execution = Execution.create(task, self.policy, agent, execution_id)
        execution_id = execution.execution_id # Ensure we use the generated one if passed None
        
        tracer = get_tracer(__name__)
        
        with tracer.start_as_current_span(
            "orchestrator.run_sync",
            attributes={
                "agent.type": getattr(agent, "name", agent.__class__.__name__),
                "agent.framework": framework,
                "task.length": len(task),
                "execution.id": execution_id
            }
        ) as span:
            start_time = time.time()
        
            self.current_execution_id = execution_id
            self.current_execution_hash = execution.execution_hash
            
            # Register execution as active
            self.persistence.register_active_execution(execution_id)

            # Save Execution Spec/Snapshot
            self.persistence.save_execution_spec(execution_id, execution.to_dict())

            if self.policy:
                self.policy.start_timer()

            status = "FAILED"
            try:
                # Replay Logic: Hydrate state if resuming
                if from_step is not None:
                    print(f"[REPLAY] Resuming execution {execution_id} from step {from_step}...")
                    # Use EventStore for replay
                    replayed_state = self.event_store.replay_to_state(execution_id, from_step)
                    
                    if not replayed_state:
                         # Fallback to legacy persistence if event store replay fails (for backward compatibility during migration)
                         history = self.persistence.get_execution_step(execution_id, from_step)
                         if not history:
                             raise ValueError(f"No state found for execution {execution_id} step {from_step}")
                         
                         saved_state = history["state"]
                         self.context.update(saved_state)
                    else:
                        # Hydrate from replayed state
                        self.context["step_count"] = replayed_state.current_step
                        self.context["token_usage"] = replayed_state.cumulative_tokens
                        self.context["tool_calls"] = replayed_state.cumulative_tool_calls
                        if replayed_state.current_state:
                             # We need to map string state back to Enum if possible, or trust the state machine
                             # For now, let's assume we resume at EXECUTE as before, or use the replayed state
                             pass

                    # Ensure agent/adapter are initialized in context
                    self._handle_init(agent, task, framework)
                    
                    # Resume at EXECUTE
                    self.state_machine.set_state(AgentState.EXECUTE)
                
                # Emit Execution Started Event
                start_event = ExecutionEvent(
                    execution_id=execution_id,
                    step_number=0,
                    event_type=EventType.EXECUTION_STARTED,
                    input_data={
                        "task": task, 
                        "agent": agent.__class__.__name__,
                        "execution_hash": execution.execution_hash
                    },
                    cumulative_tokens=0,
                    cumulative_steps=0,
                    cumulative_tool_calls=0
                )
                self.event_store.append_event(execution_id, start_event)
                self.event_bus.emit(Event(EventType.EXECUTION_STARTED, start_event.to_dict()))


                while not self.state_machine.is_terminal():

                    current_state = self.state_machine.get_state()
                    step_count = self.context.get("step_count", 0)
                    token_usage = self.context.get("token_usage", 0)
                    tool_calls_count = self.context.get("tool_calls", 0)

                    if self.policy:
                        self.policy.validate(self.context)
                    
                    self._execute_simulation_hook_sync("after_policy_validation", execution_id, step_count)
                    
                    # Start Step Span
                    with tracer.start_as_current_span(f"oao.step.{step_count}") as step_span:
                        step_span.set_attribute("step.number", step_count)
                        step_span.set_attribute("execution.id", execution_id)
                        step_span.set_attribute("agent.state", current_state.name)

                        # Create atomic Execution Event with trace context
                        event = self._create_execution_event(
                            execution_id=execution_id,
                            step_number=step_count,
                            event_type=EventType.STATE_ENTER,
                            state=current_state.name,
                            timestamp=time.time(),
                            cumulative_tokens=token_usage,
                            cumulative_steps=step_count,
                            cumulative_tool_calls=tool_calls_count
                        )
                    
                        # Persist Event (Event-Sourcing)
                        self.event_store.append_event(execution_id, event)

                        # Snapshot for quick resume (Hybrid Approach)
                        self.persistence.save_execution_step(
                            execution_id, 
                            step_count, 
                            self.context
                        )

                        self._execute_simulation_hook_sync("after_event_persistence", execution_id, step_count)

                        self.event_bus.emit(
                            Event(EventType.STATE_ENTER, {"state": current_state.name, "execution_id": execution_id})
                        )

                        if current_state == AgentState.INIT:
                            self._handle_init(agent, task, framework)
                            self.state_machine.transition(AgentState.PLAN)

                        elif current_state == AgentState.PLAN:
                            self._handle_plan()
                            self.state_machine.transition(AgentState.EXECUTE)

                        elif current_state == AgentState.EXECUTE:
                            self._handle_execute()
                            self.state_machine.transition(AgentState.REVIEW)

                        elif current_state == AgentState.REVIEW:
                            self._handle_review()
                            self.state_machine.transition(AgentState.TERMINATE)

                        else:
                            break
                
                status = "SUCCESS"
                
                # Emit Workflow Completed Event
                complete_event = ExecutionEvent(
                    execution_id=execution_id,
                    step_number=self.context.get("step_count", 0),
                    event_type=EventType.EXECUTION_COMPLETED,
                    output_data={"status": status},
                    cumulative_tokens=self.context.get("token_usage", 0),
                    cumulative_steps=self.context.get("step_count", 0),
                    cumulative_tool_calls=self.context.get("tool_calls", 0)
                )
                self.event_store.append_event(execution_id, complete_event)

            except PolicyViolation as e:
                error_event = ExecutionEvent(
                    execution_id=execution_id,
                    step_number=self.context.get("step_count", 0),
                    event_type=EventType.POLICY_VIOLATION,
                    error=str(e),
                    cumulative_tokens=self.context.get("token_usage", 0)
                )
                self.event_store.append_event(execution_id, error_event)
                
                self.event_bus.emit(
                    Event(EventType.POLICY_VIOLATION, {"error": str(e)})
                )
                self.state_machine.fail()
                metrics.failures_counter.labels(error_type="PolicyViolation").inc()
                status = "FAILED"
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))

            except (InvalidStateTransition, Exception) as e:
                print(f"[ERROR] {e}")
                
                error_event = ExecutionEvent(
                    execution_id=execution_id,
                    step_number=self.context.get("step_count", 0),
                    event_type=EventType.EXECUTION_FAILED,
                    error=str(e),
                    cumulative_tokens=self.context.get("token_usage", 0)
                )
                self.event_store.append_event(execution_id, error_event)
                
                self.state_machine.fail()
                metrics.failures_counter.labels(error_type=type(e).__name__).inc()
                status = "FAILED"
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            
            finally:
                metrics.active_agents.dec()
                try:
                    self.persistence.remove_active_execution(execution_id)
                except Exception:
                    pass

        execution_time = time.time() - start_time
        
        # Record execution metrics
        agent_type = agent.__class__.__name__
        metrics.execution_counter.labels(status=status, agent_type=agent_type).inc()
        metrics.execution_duration.labels(agent_type=agent_type).observe(execution_time)
        metrics.token_usage_counter.labels(agent_type=agent_type).inc(
            self.context.get("token_usage", 0)
        )

        report = self._generate_report(status, execution_time)
        # Ensure report has the correct execution_id
        report.execution_id = execution_id

        self.event_bus.emit(
            Event(EventType.EXECUTION_COMPLETED, {"report": report.dict()})
        )

        return report

    # =====================================================
    # ASYNC EXECUTION
    # =====================================================

    async def run_async(
        self,
        agent: Any,
        task: str,
        framework: str = "langchain",
        execution_id: Optional[str] = None,
        from_step: Optional[int] = None
    ) -> ExecutionReport:

        tracer = get_tracer(__name__)
        
        # Create canonical Execution object
        execution = Execution.create(task, self.policy, agent, execution_id)
        execution_id = execution.execution_id 

        self.current_execution_id = execution_id
        self.current_execution_hash = execution.execution_hash # Use deterministic hash from snapshot


        # Initialize persistence - Use self.persistence instead of creating new
        # Also register for async
        self.persistence.register_active_execution(execution_id)
        
        # Save Execution Spec/Snapshot
        self.persistence.save_execution_spec(execution_id, execution.to_dict())
        
        # Emit Execution Started Event
        start_event = ExecutionEvent(
            execution_id=execution_id,
            step_number=0,
            event_type=EventType.EXECUTION_STARTED,
            input_data={
                "task": task, 
                "agent": agent.__class__.__name__,
                "execution_hash": execution.execution_hash
            },
            cumulative_tokens=0,
            cumulative_steps=0,
            cumulative_tool_calls=0
        )
        self.event_store.append_event(execution_id, start_event)
        self.event_bus.emit(Event(EventType.EXECUTION_STARTED, start_event.to_dict()))

        with tracer.start_as_current_span(
            "orchestrator.run",
            attributes={
                "agent.type": getattr(agent, "name", agent.__class__.__name__),
                "agent.framework": framework,
                "task.length": len(task),
                "execution.id": execution_id
            }
        ) as span:
            metrics.active_agents.inc()
            start_time = time.time()

            if self.policy:
                self.policy.start_timer()

            status = "FAILED"
            try:
                # Replay Logic: Hydrate state if resuming
                if from_step is not None:
                    print(f"[REPLAY] Resuming execution {execution_id} from step {from_step}...")
                    
                    # Use EventStore for replay
                    replayed_state = self.event_store.replay_to_state(execution_id, from_step)
                    
                    if not replayed_state:
                         # Fallback to legacy persistence if event store replay fails
                         history = self.persistence.get_execution_step(execution_id, from_step)
                         if not history:
                             raise ValueError(f"No state found for execution {execution_id} step {from_step}")
                         
                         saved_state = history["state"]
                         self.context.update(saved_state)
                    else:
                        # Hydrate from replayed state
                        self.context["step_count"] = replayed_state.current_step
                        self.context["token_usage"] = replayed_state.cumulative_tokens
                        self.context["tool_calls"] = replayed_state.cumulative_tool_calls
                        # We trust the state machine or resume at default EXECUTE for now
                        pass

                    # Ensure agent/adapter are initialized in context
                    self._handle_init(agent, task, framework)
                    
                    # Resume at EXECUTE
                    self.state_machine.set_state(AgentState.EXECUTE)

                while not self.state_machine.is_terminal():

                    current_state = self.state_machine.get_state()
                    step_count = self.context.get("step_count", 0)
                    token_usage = self.context.get("token_usage", 0)
                    tool_calls_count = self.context.get("tool_calls", 0)

                    if self.policy:
                        self.policy.validate(self.context)
                    
                    await self._execute_simulation_hook_async("after_policy_validation", execution_id, step_count)

                    # Start Step Span (Async)
                    with tracer.start_as_current_span(f"oao.step.{step_count}") as step_span:
                        step_span.set_attribute("step.number", step_count)
                        step_span.set_attribute("execution.id", execution_id)
                        step_span.set_attribute("agent.state", current_state.name)

                        # Create atomic Execution Event with trace context
                        event = self._create_execution_event(
                            execution_id=execution_id,
                            step_number=step_count,
                            event_type=EventType.STATE_ENTER,
                            state=current_state.name,
                            timestamp=time.time(),
                            cumulative_tokens=token_usage,
                            cumulative_steps=step_count,
                            cumulative_tool_calls=tool_calls_count
                        )
                    
                        # Persist Event (Event-Sourcing)
                        self.event_store.append_event(execution_id, event)
                        
                        # Persistence: Save state at start of step
                        self.persistence.save_execution_step(
                            execution_id, 
                            step_count, 
                            self.context
                        )

                        await self._execute_simulation_hook_async("after_event_persistence", execution_id, step_count)

                        self.event_bus.emit(
                            Event(EventType.STATE_ENTER, {"state": current_state.name, "execution_id": execution_id})
                        )

                        if current_state == AgentState.INIT:
                            self._handle_init(agent, task, framework)
                            self.state_machine.transition(AgentState.PLAN)

                        elif current_state == AgentState.PLAN:
                            self._handle_plan()
                            self.state_machine.transition(AgentState.EXECUTE)

                        elif current_state == AgentState.EXECUTE:
                            await self._handle_execute_async()
                            self.state_machine.transition(AgentState.REVIEW)

                        elif current_state == AgentState.REVIEW:
                            self._handle_review()
                            self.state_machine.transition(AgentState.TERMINATE)

                        else:
                            break

                status = "SUCCESS"
                
                # Emit Workflow Completed Event
                complete_event = ExecutionEvent(
                    execution_id=execution_id,
                    step_number=self.context.get("step_count", 0),
                    event_type=EventType.EXECUTION_COMPLETED,
                    output_data={"status": status},
                    cumulative_tokens=self.context.get("token_usage", 0),
                    cumulative_steps=self.context.get("step_count", 0),
                    cumulative_tool_calls=self.context.get("tool_calls", 0)
                )
                self.event_store.append_event(execution_id, complete_event)

            except Exception as e:
                print(f"[ASYNC ERROR] {e}")
                
                error_event = ExecutionEvent(
                    execution_id=execution_id,
                    step_number=self.context.get("step_count", 0),
                    event_type=EventType.EXECUTION_FAILED,
                    error=str(e),
                    cumulative_tokens=self.context.get("token_usage", 0)
                )
                self.event_store.append_event(execution_id, error_event)
                
                self.state_machine.fail()
                metrics.failures_counter.labels(error_type=type(e).__name__).inc()
                status = "FAILED"
                
                # Trace exception
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                
            finally:
                metrics.active_agents.dec()
                try:
                    self.persistence.remove_active_execution(execution_id)
                except Exception:
                    pass

            execution_time = time.time() - start_time
            
            # Record execution metrics
            agent_type = agent.__class__.__name__
            metrics.execution_counter.labels(status=status, agent_type=agent_type).inc()
            metrics.execution_duration.labels(agent_type=agent_type).observe(execution_time)
            metrics.token_usage_counter.labels(agent_type=agent_type).inc(
                self.context.get("token_usage", 0)
            )

            report = self._generate_report(status, execution_time)

            self.event_bus.emit(
                Event(EventType.EXECUTION_COMPLETED, {"report": report.dict()})
            )

            return report

    # =====================================================
    # Lifecycle Handlers
    # =====================================================

    def _handle_init(self, agent: Any, task: str, framework: str):
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("orchestrator.init"):
            print("[INIT] Initializing agent...")
            
            try:
                AdapterClass = AdapterRegistry.get_adapter(framework)
                adapter = AdapterClass(agent)
            except Exception as e:
                # If adapter fails to load (e.g., missing dependency),
                # raise the error to fail the execution gracefully
                raise ImportError(f"Failed to load adapter for framework '{framework}': {e}")

            self.context = {
                "execution_id": getattr(self, "current_execution_id", None),
                "execution_hash": getattr(self, "current_execution_hash", None),
                "event_store": self.event_store,
                "agent": agent,
                "adapter": adapter,
                "framework": framework,
                "task": task,
                "plan": None,
                "execution_result": None,
                "final_output": None,
                "step_count": 0,
                "token_usage": 0,
                "tool_calls": 0,
            }

    def _handle_plan(self):
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("orchestrator.plan"):
            print("[PLAN] Planning task...")
            self.context["step_count"] += 1

            adapter = self.context["adapter"]
            self.context["plan"] = adapter.plan(self.context["task"])

    def _handle_execute(self):
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("orchestrator.execute"):
            print("[EXECUTE] Executing task...")
            self.context["step_count"] += 1

            adapter = self.context["adapter"]
            
            # Get retry config from policy
            retry_settings = getattr(self.policy, "retry_config", {})
            retry_config = RetryConfig(
                max_retries=retry_settings.get("max_retries", 3),
                initial_delay=retry_settings.get("initial_delay", 1.0),
                backoff_factor=retry_settings.get("backoff_factor", 2.0),
                strategy=BackoffStrategy(retry_settings.get("strategy", "EXPONENTIAL"))
            )
            
            def on_retry(attempt, exception, delay):
                event = self._create_execution_event(
                    execution_id=self.current_execution_id,
                    step_number=self.context.get("step_count", 0),
                    event_type=EventType.RETRY_ATTEMPTED,
                    error=str(exception),
                    input_data={"attempt": attempt, "delay": delay},
                    cumulative_tokens=self.context.get("token_usage", 0)
                )
                self.event_store.append_event(self.current_execution_id, event)
                self.event_bus.emit(Event(EventType.RETRY_ATTEMPTED, event.to_dict()))

            result = execute_with_retry(
                adapter.execute,
                config=retry_config,
                on_retry=on_retry,
                task=self.context["plan"],
                context=self.context,
                policy=self.policy,
            )

            self.context["execution_result"] = result
            self.context["token_usage"] += adapter.get_token_usage()

    async def _handle_execute_async(self):
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("orchestrator.execute"):
            print("[EXECUTE-ASYNC] Executing task...")
            self.context["step_count"] += 1

            adapter = self.context["adapter"]
            
            # Get retry config from policy
            retry_settings = getattr(self.policy, "retry_config", {})
            retry_config = RetryConfig(
                max_retries=retry_settings.get("max_retries", 3),
                initial_delay=retry_settings.get("initial_delay", 1.0),
                backoff_factor=retry_settings.get("backoff_factor", 2.0),
                strategy=BackoffStrategy(retry_settings.get("strategy", "EXPONENTIAL"))
            )

            def on_retry(attempt, exception, delay):
                event = self._create_execution_event(
                    execution_id=self.current_execution_id,
                    step_number=self.context.get("step_count", 0),
                    event_type=EventType.RETRY_ATTEMPTED,
                    error=str(exception),
                    input_data={"attempt": attempt, "delay": delay},
                    cumulative_tokens=self.context.get("token_usage", 0)
                )
                self.event_store.append_event(self.current_execution_id, event)
                self.event_bus.emit(Event(EventType.RETRY_ATTEMPTED, event.to_dict()))

            result = await execute_with_retry_async(
                adapter.execute_async,
                config=retry_config,
                on_retry=on_retry,
                task=self.context["plan"],
                context=self.context,
                policy=self.policy,
            )

            self.context["execution_result"] = result
            self.context["token_usage"] += adapter.get_token_usage()

    def _handle_review(self):
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("orchestrator.review"):
            print("[REVIEW] Reviewing result...")
            self.context["step_count"] += 1

            result = self.context["execution_result"]

            if isinstance(result, dict) and "output" in result:
                self.context["final_output"] = result["output"]
            else:
                self.context["final_output"] = str(result)

    # =====================================================
    # Report Generator
    # =====================================================

    def _generate_report(self, status: str, execution_time: float):

        agent_name = "Unknown"
        if self.context.get("agent"):
            agent_name = self.context["agent"].__class__.__name__

        return ExecutionReport.create(
            agent_name=agent_name,
            status=status,
            total_tokens=self.context.get("token_usage", 0),
            total_steps=self.context.get("step_count", 0),
            tool_calls=self.context.get("tool_calls", 0),
            execution_time_seconds=execution_time,
            state_history=[state.name for state in self.state_machine.get_history()],
            final_output=self.context.get("final_output"),
            execution_id=self.context.get("execution_id"), # Pass ID from context or argument
            execution_hash=self.context.get("execution_hash"),
        )
    
    def get_events(self, execution_id: str):
        """Helper to get events for an execution."""
        return self.event_store.get_events(execution_id)


