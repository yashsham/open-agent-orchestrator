import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oao.runtime.orchestrator import Orchestrator
from oao.policy.strict_policy import StrictPolicy

class TestRetryIntegration(unittest.TestCase):
    def test_retry_on_failure(self):
        # Mock Persistence to avoid redis connection
        with patch('oao.runtime.persistence.RedisPersistenceAdapter'):
            
            # Setup Orchestrator with Retry Policy
            # max_retries=2 means: try, fail, retry1, fail, retry2, success -> 3 calls total
            policy = StrictPolicy(
                max_steps=5,
                retry_config={"max_retries": 2, "initial_delay": 0.001, "backoff_factor": 1.0}
            )
            orch = Orchestrator(policy=policy)
            
            # Mock Agent
            agent = MagicMock()
            agent.name = "RetryAgent"
            
            # Mock Adapter
            mock_adapter_cls = MagicMock()
            mock_adapter = mock_adapter_cls.return_value
            
            # Plan succeeds
            mock_adapter.plan.return_value = "plan"
            
            # Execute fails twice then succeeds
            # Orchestrator will call execute_with_retry(adapter.execute)
            mock_adapter.execute.side_effect = [ValueError("fail1"), ValueError("fail2"), "success"]
            mock_adapter.execute.__name__ = "mock_execute"
            mock_adapter.get_token_usage.return_value = 10
            
            # Patch Registry to return our mock adapter
            with patch('oao.adapters.registry.AdapterRegistry.get_adapter', return_value=mock_adapter_cls):
                report = orch.run(agent, "task")
                
            # Verify adapter.execute was called 3 times (1 initial + 2 retries)
            # execute_with_retry handles the loop
            self.assertEqual(mock_adapter.execute.call_count, 3)
            self.assertEqual(report.status, "SUCCESS")

    def test_retry_exhausted(self):
        # Verify failure when retries exhausted
         with patch('oao.runtime.persistence.RedisPersistenceAdapter'):
            
            policy = StrictPolicy(
                max_steps=2,
                retry_config={"max_retries": 1, "initial_delay": 0.001}
            )
            orch = Orchestrator(policy=policy)
            
            agent = MagicMock()
            agent.name = "FailAgent"
            
            mock_adapter_cls = MagicMock()
            mock_adapter = mock_adapter_cls.return_value
            mock_adapter.plan.return_value = "plan"
            
            # Execute always fails
            mock_adapter.execute.side_effect = ValueError("persistent failure")
            mock_adapter.execute.__name__ = "mock_execute_fail"
            mock_adapter.get_token_usage.return_value = 10
            
            with patch('oao.adapters.registry.AdapterRegistry.get_adapter', return_value=mock_adapter_cls):
                report = orch.run(agent, "task")
            
            # Should have called 2 times (1 initial + 1 retry)
            self.assertEqual(mock_adapter.execute.call_count, 2)
            # Status should be FAILED
            self.assertEqual(report.status, "FAILED")

if __name__ == '__main__':
    unittest.main()
