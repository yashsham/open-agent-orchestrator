import time
import asyncio
from typing import Any, Optional

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

    # =====================================================
    # SYNC EXECUTION
    # =====================================================

    def run(self, agent: Any, task: str, framework: str = "langchain") -> ExecutionReport:

        start_time = time.time()

        if self.policy:
            self.policy.start_timer()

        try:
            while not self.state_machine.is_terminal():

                if self.policy:
                    self.policy.validate(self.context)

                current_state = self.state_machine.get_state()

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
            status = "FAILED"

        except (InvalidStateTransition, Exception) as e:
            print(f"[ERROR] {e}")
            self.state_machine.fail()
            status = "FAILED"

        execution_time = time.time() - start_time

        report = self._generate_report(status, execution_time)

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
    ) -> ExecutionReport:

        start_time = time.time()

        if self.policy:
            self.policy.start_timer()

        try:
            while not self.state_machine.is_terminal():

                if self.policy:
                    self.policy.validate(self.context)

                current_state = self.state_machine.get_state()

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
            status = "FAILED"

        execution_time = time.time() - start_time

        report = self._generate_report(status, execution_time)

        self.event_bus.emit(
            Event(EventType.EXECUTION_COMPLETE, {"report": report.dict()})
        )

        return report

    # =====================================================
    # Lifecycle Handlers
    # =====================================================

    def _handle_init(self, agent: Any, task: str, framework: str):
        print("[INIT] Initializing agent...")

        AdapterClass = AdapterRegistry.get_adapter(framework)
        adapter = AdapterClass(agent)

        self.context = {
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
        print("[PLAN] Planning task...")
        self.context["step_count"] += 1

        adapter = self.context["adapter"]
        self.context["plan"] = adapter.plan(self.context["task"])

    def _handle_execute(self):
        print("[EXECUTE] Executing task...")
        self.context["step_count"] += 1

        adapter = self.context["adapter"]

        result = adapter.execute(
            self.context["plan"],
            context=self.context,
            policy=self.policy,
        )

        self.context["execution_result"] = result
        self.context["token_usage"] += adapter.get_token_usage()

    async def _handle_execute_async(self):
        print("[EXECUTE-ASYNC] Executing task...")
        self.context["step_count"] += 1

        adapter = self.context["adapter"]

        result = await adapter.execute_async(
            self.context["plan"],
            context=self.context,
            policy=self.policy,
        )

        self.context["execution_result"] = result
        self.context["token_usage"] += adapter.get_token_usage()

    def _handle_review(self):
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
        )


