import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import asyncio
import json

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oao.runtime.recovery import RecoveryManager
from oao.runtime.persistence import RedisPersistenceAdapter

class TestRecovery(unittest.TestCase):
    
    def test_recover_crashed_execution(self):
        async def run_test():
            # Patch Persistence where it is used
            with patch('oao.runtime.recovery.RedisPersistenceAdapter') as MockPersistence:
                mock_db = MockPersistence.return_value
                
                # Setup: 1 active execution
                mock_db.list_active_executions.return_value = ["exec-123"]
                
                # Setup: Spec exists
                mock_db.load_execution_spec.return_value = {
                    "task": "Test Task",
                    "framework": "langchain",
                    "max_steps": 5,
                    "max_tokens": 100
                }
                
                # Setup: History exists (crashed at step 2)
                mock_db.get_execution_history.return_value = [
                    {"step_number": 0, "state": {}},
                    {"step_number": 1, "state": {}},
                    {"step_number": 2, "state": {}}
                ]
                
                with patch('oao.runtime.recovery.Orchestrator') as MockOrch, \
                     patch('oao.runtime.recovery.AgentFactory') as MockFactory:
                    
                    mock_run = AsyncMock()
                    MockOrch.return_value.run_async = mock_run
                    # Mock factory returns dummy agent
                    MockFactory.create_agent.return_value = MagicMock()
                    
                    manager = RecoveryManager()
                    await manager.recover_executions()
                    
                    # Yield control to allow background task to run
                    await asyncio.sleep(0.1)
                    
                    # Verify run_async called correctly
                    mock_run.assert_called_once()
                    call_args = mock_run.call_args[1] # kwargs
                    
                    self.assertEqual(call_args["execution_id"], "exec-123")
                    self.assertEqual(call_args["task"], "Test Task")
                    self.assertEqual(call_args["from_step"], 2)

        asyncio.run(run_test())

    def test_recover_no_spec(self):
        async def run_test():
             with patch('oao.runtime.recovery.RedisPersistenceAdapter') as MockPersistence:
                mock_db = MockPersistence.return_value
                mock_db.list_active_executions.return_value = ["exec-no-spec"]
                mock_db.load_execution_spec.return_value = None
                
                with patch('oao.runtime.recovery.Orchestrator') as MockOrch:
                    mock_run = AsyncMock()
                    MockOrch.return_value.run_async = mock_run

                    manager = RecoveryManager()
                    await manager.recover_executions()
                    
                    # Verify run_async NOT called
                    mock_run.assert_not_called()
                    # Verify remove_active_execution called
                    mock_db.remove_active_execution.assert_called_with("exec-no-spec")

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
