import unittest
import asyncio
import json
import fakeredis
from unittest import mock
from oao.runtime.dag import TaskGraph, TaskNode, GraphExecutor
from oao.runtime.persistence import RedisPersistenceAdapter

class MockAgent:
    def __init__(self, name, should_fail=False):
        self.name = name
        self.should_fail = should_fail
        self.call_count = 0

    async def run(self, input_str):
        self.call_count += 1
        if self.should_fail:
            raise RuntimeError(f"Simulated failure in {self.name}")
        return {"final_output": f"Output from {self.name}"}
    
    # Mock for Orchestrator usage
    def run_agent(self, *args, **kwargs):
        pass

# Mock Orchestrator to use our MockAgent logic directly
class MockOrchestrator:
    def __init__(self, policy=None):
        pass
    
    async def run_async(self, agent, task, framework):
        return await agent.run(task)

class TestDurableDAG(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.redis = fakeredis.FakeRedis(decode_responses=True)
        # Patch redis.from_url to return our fake instance
        self.redis_patcher = mock.patch('redis.from_url', return_value=self.redis)
        self.redis_patcher.start()
        
        # Patch Orchestrator to avoid real LLM calls
        self.orch_patcher = mock.patch('oao.runtime.dag.Orchestrator', MockOrchestrator)
        self.orch_patcher.start()

    def tearDown(self):
        self.redis_patcher.stop()
        self.orch_patcher.stop()

    async def test_resume_workflow(self):
        print("\nTesting Durable Workflow Resumption...")
        
        workflow_id = "test_wf_001"
        persistence_url = "redis://mock" # Trigger persistence logic
        
        # Define Graph
        # A -> B
        graph = TaskGraph()
        agent_a = MockAgent("AgentA") # Will succeed
        agent_b = MockAgent("AgentB", should_fail=True) # Will fail first time
        
        graph.add_node(TaskNode("TaskA", agent_a))
        graph.add_node(TaskNode("TaskB", agent_b, dependencies=["TaskA"]))

        # Run 1: Should Fail at TaskB
        executor = GraphExecutor(graph, workflow_id=workflow_id, persistence_url=persistence_url)
        
        print("▶️ Run 1: Expecting Failure at TaskB")
        try:
            await executor.execute_async("Do work")
        except RuntimeError as e:
            print(f"✅ Caught expected error: {e}")
        
        # Verify State in Redis
        adapter = RedisPersistenceAdapter() # Connects to same fake redis
        nodes = adapter.load_all_nodes(workflow_id)
        
        self.assertEqual(nodes["TaskA"]["status"], "COMPLETED")
        self.assertEqual(nodes["TaskB"]["status"], "FAILED")
        self.assertEqual(agent_a.call_count, 1)
        self.assertEqual(agent_b.call_count, 1)
        print("✅ TaskA saved as COMPLETED, TaskB as FAILED")

        # Run 2: Resume (Fix AgentB failure)
        print("▶️ Run 2: Resuming with fixed AgentB")
        agent_b.should_fail = False # Fix the bug
        
        # Re-initialize executor with SAME workflow_id
        executor_resume = GraphExecutor(graph, workflow_id=workflow_id, persistence_url=persistence_url)
        results = await executor_resume.execute_async("Do work")
        
        # Verify TaskA was SKIPPED (call_count should still be 1)
        self.assertEqual(agent_a.call_count, 1)
        # Verify TaskB ran again (call_count should be 2)
        self.assertEqual(agent_b.call_count, 2)
        
        self.assertEqual(results["TaskA"]["final_output"], "Output from AgentA")
        self.assertEqual(results["TaskB"]["final_output"], "Output from AgentB")
        print("✅ TaskA skipped, TaskB re-executed. Workflow completed.")

if __name__ == "__main__":
    unittest.main()
