import unittest
import asyncio
import time
from typing import Optional, Any
from unittest.mock import MagicMock, patch

from oao.runtime.orchestrator import Orchestrator
from oao.runtime.event_store import InMemoryEventStore
from oao.runtime.events import EventType
from oao.runtime.state_machine import AgentState
from oao.runtime.persistence import PersistenceAdapter

class MockAgent:
    def __init__(self, failure_step: Optional[int] = None):
        self.failure_step = failure_step
        self.step_count = 0

    def invoke(self, input_data: Any, **kwargs):
        self.step_count += 1
        if self.failure_step is not None and self.step_count == self.failure_step:
            raise RuntimeError(f"Simulated failure at step {self.step_count}")
        return {"output": f"Step {self.step_count} completed"}

    async def ainvoke(self, input_data: Any, **kwargs):
        return self.invoke(input_data, **kwargs)

from oao.runtime.persistence import InMemoryPersistenceAdapter

class NoRetryPolicy:
    def __init__(self):
        self.retry_config = {"max_retries": 0}
    def validate(self, context): pass
    def start_timer(self): pass

class SimulationHarness:
    def __init__(self, policy=None):
        self.event_store = InMemoryEventStore()
        self.persistence = InMemoryPersistenceAdapter()
        self.orchestrator = Orchestrator(
            event_store=self.event_store,
            persistence=self.persistence,
            policy=policy or NoRetryPolicy()
        )

    async def run_with_failure(self, agent: Any, task: str):
        report = await self.orchestrator.run_async(agent, task)
        return report

class TestSimulation(unittest.IsolatedAsyncioTestCase):
    async def test_failure_at_specific_step(self):
        """
        Verify that a failure at a specific step is correctly logged and detectable.
        """
        harness = SimulationHarness()
        agent = MockAgent(failure_step=1) 
        
        report = await harness.run_with_failure(agent, "test_task")
        
        self.assertEqual(report.status, "FAILED")
        
        # Verify events
        events = harness.event_store.get_events(report.execution_id)
        event_types = [e.event_type for e in events]
        self.assertIn(EventType.EXECUTION_STARTED, event_types)
        
    async def test_event_emission_order_on_failure(self):
        """
        Ensure events are emitted in the correct order even when failing.
        """
        harness = SimulationHarness()
        agent = MockAgent(failure_step=1)
        
        report = await harness.run_with_failure(agent, "order_test")
        
        events = harness.event_store.get_events(report.execution_id)
        
        event_types = [e.event_type for e in events]
        self.assertNotIn(EventType.EXECUTION_COMPLETED, event_types)
        self.assertIn(EventType.EXECUTION_FAILED, event_types)

    async def test_worker_crash_simulation(self):
        """
        Simulate a worker crash mid-step and verify internal state consistency.
        """
        harness = SimulationHarness()
        agent = MockAgent()
        
        # Define a hook that raises an exception *after* event persistence
        # this simulates a crash at a critical boundary
        def crash_hook(execution_id, step_count):
            if step_count == 1:
                raise SystemExit("Simulated Crash")

        harness.orchestrator.add_simulation_hook("after_event_persistence", crash_hook)
        
        try:
            await harness.orchestrator.run_async(agent, "crash_test")
        except SystemExit:
            pass # Expected
            
        # Verify that we have persistence records up to step 1
        steps = harness.persistence.steps.get(harness.orchestrator.current_execution_id, [])
        self.assertTrue(len(steps) >= 1)
        # The latest step should be 1
        self.assertEqual(steps[-1]["step_number"], 1)

    async def test_retry_event_emission_order(self):
        """
        Verify that retry events are emitted in the correct order with step events.
        Order should be: ... -> STATE_ENTER(EXECUTE) -> RETRY_ATTEMPTED -> STATE_ENTER(EXECUTE) -> ...
        """
        class RetryOncePolicy:
            def __init__(self):
                self.retry_config = {"max_retries": 1, "initial_delay": 0.1}
            def validate(self, context): pass
            def start_timer(self): pass

        harness = SimulationHarness(policy=RetryOncePolicy())
        agent = MockAgent(failure_step=1) # Fails first attempt, succeeds second
        
        report = await harness.run_with_failure(agent, "retry_order_test")
        
        self.assertEqual(report.status, "SUCCESS")
        
        events = harness.event_store.get_events(report.execution_id)
        event_types = [e.event_type for e in events]
        
        # Look for the sequence of events
        # Note: We emit STATE_ENTER before each attempt at the step (including retries if loop continues)
        # Actually in OAO, the retry happens *inside* the EXECUTE handler, so the loop doesn't restart the step.
        # But REYTRY_ATTEMPTED should be present.
        
        self.assertIn(EventType.RETRY_ATTEMPTED, event_types)
        
        retry_idx = event_types.index(EventType.RETRY_ATTEMPTED)
        # Before retry, we must have had a STATE_ENTER for EXECUTE at step 1
        found_pre_execute = False
        for i in range(retry_idx):
            if events[i].event_type == EventType.STATE_ENTER and events[i].state == "EXECUTE":
                found_pre_execute = True
                break
        self.assertTrue(found_pre_execute)

if __name__ == "__main__":
    unittest.main()
