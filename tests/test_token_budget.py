import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oao.runtime.orchestrator import Orchestrator
from oao.policy.strict_policy import StrictPolicy
from oao.runtime.events import EventType

class TestTokenBudget(unittest.TestCase):
    def test_token_limit_exceeded(self):
        # Setup Policy with tight token limit
        policy = StrictPolicy(max_tokens=50)
        
        # Mock Persistence
        with patch('oao.runtime.persistence.RedisPersistenceAdapter'):
            orch = Orchestrator(policy=policy)
            
            agent = MagicMock()
            agent.name = "TokenAgent"
            
            mock_adapter_cls = MagicMock()
            mock_adapter = mock_adapter_cls.return_value
            mock_adapter.plan.return_value = "plan"
            
            # Execute returns usage 100 > 50
            mock_adapter.execute.return_value = {"output": "result", "usage": {"total_tokens": 100}}
            mock_adapter.get_token_usage.return_value = 100
            
            with patch('oao.adapters.registry.AdapterRegistry.get_adapter', return_value=mock_adapter_cls):
                report = orch.run(agent, "task")
            
            # Should be FAILED
            self.assertEqual(report.status, "FAILED")
            
            # Check for PolicyViolation event or metrics if possible
            # But status FAILED is good enough for high level check
            
            # Also verify steps
            # INIT -> PLAN -> EXECUTE (consumes 100) -> Validation (fails)
            # So REVIEW state is never entered (or entered but validation fails immediately)
            # validate() is called inside loop.
            # 1. INIT. validate ok. -> PLAN
            # 2. PLAN. validate ok. -> EXECUTE
            # 3. EXECUTE. validate ok. Runs _handle_execute. Usage += 100. -> REVIEW
            # 4. REVIEW. validate FAILS (100 > 50). Raises PolicyViolation.
            # So _handle_review is NOT called.
            
            self.assertFalse("final_output" in orch.context and orch.context["final_output"])


if __name__ == '__main__':
    unittest.main()
