import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import asyncio

import logging

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oao.runtime.recovery import RecoveryManager, MAX_RECOVERY_ATTEMPTS

# Enable logging
logging.basicConfig(level=logging.INFO)

class TestRecovery(unittest.TestCase):
    def setUp(self):
        self.mock_persistence = MagicMock()
        self.mock_event_store = MagicMock()
        
        # Patch Persistence and EventStore in recovery module
        self.persistence_patcher = patch('oao.runtime.recovery.RedisPersistenceAdapter', return_value=self.mock_persistence)
        self.event_store_patcher = patch('oao.runtime.recovery.RedisEventStore', return_value=self.mock_event_store)
        
        self.persistence_patcher.start()
        self.event_store_patcher.start()
        
    def tearDown(self):
        self.persistence_patcher.stop()
        self.event_store_patcher.stop()

    def test_recover_success(self):
        async def run_test():
            self.mock_persistence.list_active_executions.return_value = ["exec-1"]
            self.mock_persistence.get_recovery_count.return_value = 0
            
            # Valid Spec
            spec = {
                "execution_id": "exec-1",
                "execution_hash": "hash-1",
                "snapshot": {
                    "task": "Test Task",
                    "policy_config": {},
                    "agent_config": {},
                    "tool_config": [],
                    "runtime_version": "1.1.0"
                }
            }
            self.mock_persistence.load_execution_spec.return_value = spec
            
            # Event Store returns last event at step 5
            mock_event = MagicMock()
            mock_event.step_number = 5
            self.mock_event_store.get_latest_event.return_value = mock_event
            
            # Mock Execution validation and Orchestrator
            with patch('oao.runtime.recovery.Execution.from_dict') as MockExecution, \
                 patch('oao.runtime.recovery.Orchestrator') as MockOrch, \
                 patch('oao.runtime.recovery.AgentFactory') as MockFactory:
                
                mock_exec_obj = MagicMock()
                mock_exec_obj.validate_hash.return_value = True
                MockExecution.return_value = mock_exec_obj
                
                mock_run = AsyncMock()
                MockOrch.return_value.run_async = mock_run

                MockFactory.create_agent.return_value = MagicMock()
                
                manager = RecoveryManager()
                await manager.recover_executions()
                await asyncio.sleep(0.1) # Let background task run
                
                mock_run.assert_called_once()
                call_args = mock_run.call_args[1]
                self.assertEqual(call_args["execution_id"], "exec-1")
                self.assertEqual(call_args["from_step"], 5)
                
                self.mock_persistence.increment_recovery_count.assert_called_with("exec-1")

        asyncio.run(run_test())

    def test_recover_max_attempts_exceeded(self):
        async def run_test():
            self.mock_persistence.list_active_executions.return_value = ["exec-2"]
            self.mock_persistence.get_recovery_count.return_value = MAX_RECOVERY_ATTEMPTS
            
            manager = RecoveryManager()
            await manager.recover_executions()
            
            self.mock_persistence.remove_active_execution.assert_called_with("exec-2")
            self.mock_persistence.load_execution_spec.assert_not_called()

        asyncio.run(run_test())

    def test_recover_hash_mismatch(self):
        async def run_test():
            self.mock_persistence.list_active_executions.return_value = ["exec-3"]
            self.mock_persistence.get_recovery_count.return_value = 0
            self.mock_persistence.load_execution_spec.return_value = {"some": "spec"}
             
            with patch('oao.runtime.recovery.Execution.from_dict') as MockExecution:
                mock_exec_obj = MagicMock()
                mock_exec_obj.validate_hash.return_value = False # INVALID
                mock_exec_obj.execution_id = "exec-3"
                MockExecution.return_value = mock_exec_obj
                
                manager = RecoveryManager()
                await manager.recover_executions()
                
                self.mock_persistence.remove_active_execution.assert_called_with("exec-3")
                
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
