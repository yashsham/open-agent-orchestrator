import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import time
from oao.runtime.orchestrator import Orchestrator
from oao.policy.strict_policy import StrictPolicy, PolicyViolation
from oao.runtime.events import EventType

class TestPolicyEnforcement(unittest.TestCase):

    def setUp(self):
        self.mock_agent = MagicMock()
        self.mock_agent.__class__.__name__ = "MockAgent"
        self.mock_adapter = MagicMock()
        
        # Patch AdapterRegistry to return our mock adapter
        self.patcher = patch('oao.runtime.orchestrator.AdapterRegistry')
        self.MockRegistry = self.patcher.start()
        self.MockRegistry.get_adapter.return_value = MagicMock(return_value=self.mock_adapter)
        
        # Setup default adapter behavior
        self.mock_adapter.plan.return_value = "Mock Plan"
        self.mock_adapter.execute.return_value = {"output": "Mock Output"}
        self.mock_adapter.get_token_usage.return_value = 10

    def tearDown(self):
        self.patcher.stop()

    def test_max_steps_enforcement(self):
        """Verify execution stops when max_steps is exceeded."""
        policy = StrictPolicy(max_steps=1, max_tokens=1000)
        
        # Mock persistence to avoid Redis connection
        mock_persistence = MagicMock()
        mock_event_store = MagicMock()
        # We need real event store behavior for get_events? 
        # Or mock it and assert append_event was called?
        # The test checks get_events. So we should use InMemoryEventStore or a functional mock.
        from oao.runtime.event_store import InMemoryEventStore
        event_store = InMemoryEventStore()
        
        orchestrator = Orchestrator(policy=policy, event_store=event_store, persistence=mock_persistence)
        
        # Mock state machine to loop 5 times without built-in termination
        # But policy should stop it at 3 (check > 2)
        # Orchestrator loop checks policy.validate() at start.
        # Step 0 (Init) -> Step 1 (Plan) -> Step 2 (Execute) -> Step 3 (Review/Execute)
        # StrictPolicy checks context["step_count"].
        
        # Orchestrator increments step_count in handlers.
        # Context init: step_count = 0.
        # _handle_plan: step_count += 1 (Total 1).
        # _handle_execute: step_count += 1 (Total 2).
        # Next loop: validate. steps=2. max_steps=2. 2 > 2 False.
        # _handle_review: step_count += 1 (Total 3).
        # Next loop: validate. steps=3. 3 > 2 True. Raise!
        
        report = orchestrator.run(self.mock_agent, "Task")
        
        self.assertEqual(report.status, "FAILED")
        # Check events for violation
        events = orchestrator.get_events(report.execution_id)
        violation_events = [e for e in events if e.event_type == EventType.POLICY_VIOLATION]
        self.assertTrue(len(violation_events) > 0)
        self.assertEqual(violation_events[0].error, "Maximum execution steps exceeded")

    def test_max_tokens_enforcement(self):
        """Verify execution stops when max_tokens is exceeded."""
        policy = StrictPolicy(max_steps=10, max_tokens=100)
        orchestrator = Orchestrator(policy=policy)
        
        # Configure adapter to consume tokens
        # Step 1 (Plan): 0 tokens (default)
        # Step 2 (Execute): 60 tokens
        # Step 3 (Execute again?): 60 tokens -> Total 120.
        
        self.mock_adapter.get_token_usage.return_value = 60 # Exceeds 50 immediately
        # If we loop back to Execute? Orchestrator default loop goes Init->Plan->Execute->Review->Terminate.
        # It doesn't loop Execute unless AgentState says so.
        # Standard StateMachine goes linear.
        
        # I need to force a loop to trigger multiple executions.
        # OR set max_tokens very low (e.g. 10) and have first execute return 20.
        
        policy = StrictPolicy(max_steps=10, max_tokens=50)
        
        mock_persistence = MagicMock()
        from oao.runtime.event_store import InMemoryEventStore
        event_store = InMemoryEventStore()
        
        orchestrator = Orchestrator(policy=policy, event_store=event_store, persistence=mock_persistence)
        
        self.mock_adapter.get_token_usage.return_value = 60 # Exceeds 50 immediately
        
        report = orchestrator.run(self.mock_agent, "Task")
        
        # Run 1:
        # ...
        # Execute: usage becomes 60.
        # Review: usage 60.
        # Terminate.
        # Policy is checked at start of loop.
        # Loop 1 (Init): usage 0. OK.
        # Loop 2 (Plan): usage 0. OK.
        # Loop 3 (Execute): usage 0. OK. (Update occurs AFTER check).
        # Loop 4 (Review): usage 60. 60 > 50. VIOLATION!
        
        self.assertEqual(report.status, "FAILED")
        # Check events.
        
        events = orchestrator.get_events(report.execution_id)
        violation_events = [e for e in events if e.event_type == EventType.POLICY_VIOLATION]
        self.assertTrue(len(violation_events) > 0)
        self.assertEqual(violation_events[0].error, "Maximum token limit exceeded")
        
if __name__ == '__main__':
    unittest.main()
