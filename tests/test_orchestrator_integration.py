import unittest
import asyncio
from unittest.mock import MagicMock, patch
from oao.runtime.orchestrator import Orchestrator
from oao.runtime.event_store import InMemoryEventStore
from oao.runtime.events import EventType
from oao.policy.strict_policy import StrictPolicy
from oao.runtime.state_machine import AgentState
from oao.runtime.execution import ExecutionStatus

class MockAdapter:
    def __init__(self, agent):
        self.agent = agent
        self.token_usage = 100

    def plan(self, task):
        return {"steps": ["step1", "step2"]}
    
    async def aplan(self, task):
        return {"steps": ["step1", "step2"]}

    def execute(self, task, context, policy=None):
        return {"output": "result", "token_usage": 50}

    async def execute_async(self, task, context, policy=None):
        return {"output": "result", "token_usage": 50}

    def get_token_usage(self):
        return self.token_usage

class MockAgent:
    def __init__(self):
        self.name = "MockAgent"

class TestEventSourcedOrchestrator(unittest.TestCase):
    def setUp(self):
        from oao.runtime.persistence import InMemoryPersistenceAdapter
        self.event_store = InMemoryEventStore()
        self.persistence = InMemoryPersistenceAdapter()
        self.orchestrator = Orchestrator(
            policy=StrictPolicy(max_steps=5),
            event_store=self.event_store,
            persistence=self.persistence
        )
        
        # Patch AdapterRegistry to return MockAdapter
        self.patcher = patch('oao.adapters.registry.AdapterRegistry.get_adapter', return_value=lambda x: MockAdapter(x))
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_run_sync_emits_events(self):
        agent = MockAgent()
        task = "Test Sync Task"
        
        report = self.orchestrator.run(agent, task)
        
        self.assertEqual(report.status, "SUCCESS")
        
        # Verify events
        events = self.event_store.get_events(report.execution_id)
        self.assertGreater(len(events), 0)
        
        # Check specific event sequence
        event_types = [e.event_type for e in events]
        self.assertIn(EventType.EXECUTION_STARTED, event_types)
        self.assertIn(EventType.STATE_ENTER, event_types) # Multiple state enters
        self.assertIn(EventType.EXECUTION_COMPLETED, event_types)
        
        # Check cumulative metrics
        completion_event = events[-1]
        self.assertEqual(completion_event.event_type, EventType.EXECUTION_COMPLETED)
        self.assertGreater(completion_event.cumulative_tokens, 0)
        self.assertGreater(completion_event.cumulative_steps, 0)
        
        # Check Timeline
        timeline = self.event_store.get_execution_timeline(report.execution_id)
        self.assertEqual(timeline["status"], "COMPLETED")

    def test_run_async_emits_events(self):
        agent = MockAgent()
        task = "Test Async Task"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            report = loop.run_until_complete(self.orchestrator.run_async(agent, task))
        finally:
            loop.close()
            
        self.assertEqual(report.status, "SUCCESS")
        
        # Verify events
        events = self.event_store.get_events(report.execution_id)
        self.assertGreater(len(events), 0)
        
        # Check specific event sequence
        event_types = [e.event_type for e in events]
        self.assertIn(EventType.EXECUTION_STARTED, event_types)
        self.assertIn(EventType.STATE_ENTER, event_types)
        self.assertIn(EventType.EXECUTION_COMPLETED, event_types)
        
        # Check cumulative metrics on completion
        completion_event = events[-1]
        self.assertEqual(completion_event.event_type, EventType.EXECUTION_COMPLETED)
        self.assertGreater(completion_event.cumulative_tokens, 0)

    def test_replay_from_events(self):
        """Test that we can replay checks and resume execution"""
        agent = MockAgent()
        task = "Test Replay Task"
        
        # Run first execution
        report1 = self.orchestrator.run(agent, task)
        exec_id = report1.execution_id
        
        # Get events up to PLAN state
        events = self.event_store.get_events(exec_id)
        # Identify step number for PLAN state
        plan_step = next(e.step_number for e in events if e.state == "PLAN")
        
        # Create new orchestrator for replay
        replay_orchestrator = Orchestrator(
            policy=StrictPolicy(max_steps=5),
            event_store=self.event_store, # Share same event store
            persistence=self.persistence
        )
        
        # Resume from plan step
        # Since we mocked persistence, we need to mock get_execution_step if it falls back
        # But our new logic uses event_store first!
        
        report2 = replay_orchestrator.run(
            agent, 
            task, 
            execution_id=exec_id,
            from_step=plan_step
        )
        
        self.assertEqual(report2.status, "SUCCESS")
        self.assertEqual(report2.execution_id, exec_id)
        
        # Verify new events appended
        new_events = self.event_store.get_events(exec_id)
        self.assertGreater(len(new_events), len(events))


if __name__ == '__main__':
    unittest.main()
