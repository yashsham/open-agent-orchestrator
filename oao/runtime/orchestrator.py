import time
import asyncio
from typing import Any, Optional
import time
import uuid
import asyncio
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
from oao.runtime.events import Event, EventType
from oao.runtime.default_logger import console_logger
import oao.adapters.langchain_adapter # Ensure registration
import oao.metrics as metrics
from oao.runtime.hashing import compute_execution_hash
from oao.runtime.resilience import execute_with_retry, execute_with_retry_async


class Orchestrator:
    """
    Main runtime controller for OpenAgentOrchestrator.
    Supports both sync and async execution.
    """

    def __init__(self, policy: Optional[Any] = None):
        self.state_machine = StateMachine()
        self.policy = policy
        self.context = {}
        self.event_bus = EventBus()

        # Register default event hooks
        self.event_bus.register(EventType.STATE_ENTER, console_logger)
        self.event_bus.register(EventType.POLICY_VIOLATION, console_logger)
        self.event_bus.register(EventType.EXECUTION_COMPLETE, console_logger)

        # Register global listeners
        # Register global listeners
        from oao.runtime.events import GlobalEventRegistry
        for event_type in EventType:
            for listener in GlobalEventRegistry.get_listeners(event_type):
                self.event_bus.register(event_type, listener)

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
        
        tracer = get_tracer(__name__)
        
        # Initialize execution ID if not provided (normal run)
        if not execution_id:
            execution_id = str(uuid.uuid4())
            
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
                
            # Compute deterministic execution hash
            self.current_execution_hash = compute_execution_hash(task, self.policy, agent)

            # Initialize persistence
            # TODO: Inject persistence adapter properly in future refactor
            from oao.runtime.persistence import RedisPersistenceAdapter
            persistence = RedisPersistenceAdapter()
            persistence.register_active_execution(execution_id)

            if self.policy:
                self.policy.start_timer()

            status = "FAILED"
            try:
                # Replay Logic: Hydrate state if resuming
                if from_step is not None:
                    print(f"[REPLAY] Resuming execution {execution_id} from step {from_step}...")
                    history = persistence.get_execution_step(execution_id, from_step)
                    if not history:
                        raise ValueError(f"No state found for execution {execution_id} step {from_step}")
                    
                    # Ensure agent/adapter are initialized in context
                    self._handle_init(agent, task, framework)
                    
                    # Restore context by merging saved state
                    # This preserves agent/adapter while updating data/metrics
                    saved_state = history["state"]
                    self.context.update(saved_state)
                    
                    # Verify deterministic hash
                    saved_hash = saved_state.get("execution_hash")
                    if saved_hash and saved_hash != self.current_execution_hash:
                        print(f"[WARNING] Replay hash mismatch! Saved: {saved_hash}, Current: {self.current_execution_hash}")
                        # In future, we might raise PolicyViolation here if strict determinism is required

                    # Resume at EXECUTE
                    self.state_machine.set_state(AgentState.EXECUTE)
                
                while not self.state_machine.is_terminal():

                    if self.policy:
                        self.policy.validate(self.context)

                    current_state = self.state_machine.get_state()
                    
                    # Persistence: Save state at start of step
                    persistence.save_execution_step(
                        execution_id, 
                        self.context.get("step_count", 0), 
                        self.context
                    )

                    self.event_bus.emit(
                        Event(EventType.STATE_ENTER, {"state": current_state.name})
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

            except PolicyViolation as e:
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
                self.state_machine.fail()
                metrics.failures_counter.labels(error_type=type(e).__name__).inc()
                status = "FAILED"
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            
            finally:
                metrics.active_agents.dec()
                try:
                    persistence.remove_active_execution(execution_id)
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
            Event(EventType.EXECUTION_COMPLETE, {"report": report.dict()})
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
        
        # Initialize execution ID if not provided (normal run)
        if not execution_id:
            execution_id = str(uuid.uuid4())
        
        self.current_execution_id = execution_id

        # Compute deterministic execution hash
        self.current_execution_hash = compute_execution_hash(task, self.policy, agent)

        # Initialize persistence
        from oao.runtime.persistence import RedisPersistenceAdapter
        persistence = RedisPersistenceAdapter()
        persistence.register_active_execution(execution_id)
        
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
                    history = persistence.get_execution_step(execution_id, from_step)
                    if not history:
                        raise ValueError(f"No state found for execution {execution_id} step {from_step}")
                    
                    # Ensure agent/adapter are initialized in context
                    self._handle_init(agent, task, framework)
                    
                    # Restore context by merging saved state
                    saved_state = history["state"]
                    self.context.update(saved_state)
                    
                    # Verify deterministic hash
                    saved_hash = saved_state.get("execution_hash")
                    if saved_hash and saved_hash != self.current_execution_hash:
                        print(f"[WARNING] Replay hash mismatch! Saved: {saved_hash}, Current: {self.current_execution_hash}")

                    # Resume at EXECUTE
                    self.state_machine.set_state(AgentState.EXECUTE)

                while not self.state_machine.is_terminal():

                    if self.policy:
                        self.policy.validate(self.context)

                    current_state = self.state_machine.get_state()
                    
                    # Persistence: Save state at start of step
                    persistence.save_execution_step(
                        execution_id, 
                        self.context.get("step_count", 0), 
                        self.context
                    )

                    self.event_bus.emit(
                        Event(EventType.STATE_ENTER, {"state": current_state.name})
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

            except Exception as e:
                print(f"[ASYNC ERROR] {e}")
                self.state_machine.fail()
                metrics.failures_counter.labels(error_type=type(e).__name__).inc()
                status = "FAILED"
                
                # Trace exception
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                
            finally:
                metrics.active_agents.dec()
                try:
                    persistence.remove_active_execution(execution_id)
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
                Event(EventType.EXECUTION_COMPLETE, {"report": report.dict()})
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
                "execution_id": getattr(self, "current_execution_id", None), # We'll set this property in run()
                "execution_hash": getattr(self, "current_execution_hash", None),
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
            retry_config = getattr(self.policy, "retry_config", {})
            
            result = execute_with_retry(
                adapter.execute,
                max_retries=retry_config.get("max_retries", 0),
                initial_delay=retry_config.get("initial_delay", 1.0),
                backoff_factor=retry_config.get("backoff_factor", 2.0),
                # retry_on defaults to catch generic Exception, which is broad but safe for v1
                plan=self.context["plan"],
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
            retry_config = getattr(self.policy, "retry_config", {})

            result = await execute_with_retry_async(
                adapter.execute_async,
                max_retries=retry_config.get("max_retries", 0),
                initial_delay=retry_config.get("initial_delay", 1.0),
                backoff_factor=retry_config.get("backoff_factor", 2.0),
                plan=self.context["plan"],
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


