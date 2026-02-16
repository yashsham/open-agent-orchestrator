import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oao.runtime.orchestrator import Orchestrator
from oao.policy.strict_policy import StrictPolicy

# Mock LangChain Agent
class MockAgent:
    def __init__(self):
        self.name = "IntegrationTestAgent"
    
    def invoke(self, input_data):
        return {"output": "result"}

class TestHashIntegration(unittest.TestCase):

    def setUp(self):
        # Mock persistence to avoid redis dependency in unit test
        # We patch RedisPersistenceAdapter construction or just let it fail/mock it
        # Since Orchestrator imports it inside run(), we need to patch sys.modules or similar?
        # Or patch Orchestrator's internal import? Hard because it's inside the function.
        # But wait, local import inside run(): `from oao.runtime.persistence import RedisPersistenceAdapter`
        # We can mock `oao.runtime.persistence.RedisPersistenceAdapter` BEFORE calling run.
        
        # But Orchestrator has `import oao.adapters.langchain_adapter` at top level.
        pass

    def test_run_generates_hash(self):
        from oao.runtime.persistence import InMemoryPersistenceAdapter
        from oao.runtime.event_store import InMemoryEventStore
        
        # Setup Orchestrator with InMemory adapters
        persistence = InMemoryPersistenceAdapter()
        event_store = InMemoryEventStore()
        orch = Orchestrator(persistence=persistence, event_store=event_store, policy=StrictPolicy(max_steps=2))
        agent = MockAgent()
        
        # Run
        report = orch.run(agent, "test task")
        
        # Verify hash
        self.assertIsNotNone(report.execution_hash)
        print(f"Sync Execution Hash: {report.execution_hash}")
        self.assertTrue(len(report.execution_hash) == 64) # SHA256 length

    def test_async_run_generates_hash(self):
        # Async test wrapper
        async def run_test():
            from oao.runtime.persistence import InMemoryPersistenceAdapter
            from oao.runtime.event_store import InMemoryEventStore
            
            persistence = InMemoryPersistenceAdapter()
            event_store = InMemoryEventStore()
            orch = Orchestrator(persistence=persistence, event_store=event_store, policy=StrictPolicy(max_steps=2))
            agent = MockAgent()
            
            report = await orch.run_async(agent, "test task async")
            
            self.assertIsNotNone(report.execution_hash)
            print(f"Async Execution Hash: {report.execution_hash}")
            self.assertTrue(len(report.execution_hash) == 64)

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
