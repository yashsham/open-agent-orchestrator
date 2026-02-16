import unittest
from oao.runtime.execution import Execution
from oao.policy.strict_policy import StrictPolicy

class MockAgent:
    def __init__(self, name="TestAgent"):
        self.name = name
    def invoke(self, task):
        pass

class MockTool:
    def __init__(self, name, description):
        self.name = name
        self.description = description

class MockAgentWithTools:
    def __init__(self, name="ToolAgent"):
        self.name = name
        self.tools = [MockTool("tool1", "desc1"), MockTool("tool2", "desc2")]

class TestExecutionModel(unittest.TestCase):

    def test_execution_creation(self):
        policy = StrictPolicy(max_steps=5)
        agent = MockAgent()
        task = "Test task"
        
        exec_obj = Execution.create(task, policy, agent)
        
        self.assertIsNotNone(exec_obj.execution_id)
        self.assertIsNotNone(exec_obj.execution_hash)
        
        # Use to_dict() to access snapshot data
        snapshot_dict = exec_obj.snapshot.to_dict()
        self.assertEqual(snapshot_dict["task"], task)
        self.assertEqual(snapshot_dict["policy_config"]["max_steps"], 5)
        self.assertEqual(snapshot_dict["agent_config"]["name"], "TestAgent")
        self.assertEqual(snapshot_dict["runtime_version"], "1.1.0")

    def test_deterministic_hash(self):
        policy = StrictPolicy(max_steps=5)
        agent = MockAgent()
        task = "Test task"
        
        exec1 = Execution.create(task, policy, agent)
        exec2 = Execution.create(task, policy, agent)
        
        # Hashes should be identical for identical inputs
        self.assertEqual(exec1.execution_hash, exec2.execution_hash)
        # IDs should be different
        self.assertNotEqual(exec1.execution_id, exec2.execution_id)

    def test_hash_sensitivity(self):
        agent = MockAgent()
        task = "Test task"
        
        # Policy change changes hash
        exec1 = Execution.create(task, StrictPolicy(max_steps=5), agent)
        exec2 = Execution.create(task, StrictPolicy(max_steps=6), agent)
        self.assertNotEqual(exec1.execution_hash, exec2.execution_hash)
        
        # Task change changes hash
        exec3 = Execution.create("Task A", StrictPolicy(), agent)
        exec4 = Execution.create("Task B", StrictPolicy(), agent)
        self.assertNotEqual(exec3.execution_hash, exec4.execution_hash)

    def test_tools_inclusion(self):
        agent1 = MockAgent()
        agent2 = MockAgentWithTools()
        
        # Agent with tools should have different hash than agent without (even if names same/similar)
        # Here classes are different so hash differs by class name too.
        # Let's use same class name mock if needed, but class name is part of identity.
        
        exec1 = Execution.create("task", None, agent1)
        exec2 = Execution.create("task", None, agent2)
        
        self.assertNotEqual(exec1.execution_hash, exec2.execution_hash)
        
        # Use to_dict() to access tool config
        snapshot_dict = exec2.snapshot.to_dict()
        self.assertEqual(len(snapshot_dict["tool_config"]), 2)
        self.assertEqual(snapshot_dict["tool_config"][0]["name"], "tool1")

if __name__ == '__main__':
    unittest.main()
