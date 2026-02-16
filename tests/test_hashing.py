import unittest
import sys
import os

# Ensure local package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oao.runtime.hashing import compute_execution_hash
from oao.policy.strict_policy import StrictPolicy

class MockAgent:
    name = "TestAgent"

class TestHashing(unittest.TestCase):
    def test_deterministic_hash(self):
        task = "test task"
        policy = StrictPolicy(max_steps=5)
        agent = MockAgent()
        
        hash1 = compute_execution_hash(task, policy, agent)
        hash2 = compute_execution_hash(task, policy, agent)
        
        self.assertEqual(hash1, hash2)
        
    def test_different_task(self):
        policy = StrictPolicy(max_steps=5)
        agent = MockAgent()
        
        hash1 = compute_execution_hash("task A", policy, agent)
        hash2 = compute_execution_hash("task B", policy, agent)
        
        self.assertNotEqual(hash1, hash2)
        
    def test_different_policy(self):
        task = "test task"
        agent = MockAgent()
        
        hash1 = compute_execution_hash(task, StrictPolicy(max_steps=5), agent)
        hash2 = compute_execution_hash(task, StrictPolicy(max_steps=10), agent)
        
        self.assertNotEqual(hash1, hash2)

    def test_different_agent(self):
        task = "test task"
        policy = StrictPolicy(max_steps=5)
        
        class AgentA:
            name = "A"
            
        class AgentB:
            name = "B"
            
        hash1 = compute_execution_hash(task, policy, AgentA())
        hash2 = compute_execution_hash(task, policy, AgentB())
        
        
        self.assertNotEqual(hash1, hash2)

    def test_different_tools(self):
        task = "test task"
        policy = StrictPolicy(max_steps=5)
        
        class MockTool:
            def __init__(self, name):
                self.name = name
                
        class AgentWithTools:
            def __init__(self, tools):
                self.tools = tools
                self.name = "AgentWithTools"
                
        agent1 = AgentWithTools([MockTool("tool1")])
        agent2 = AgentWithTools([MockTool("tool2")])
        
        hash1 = compute_execution_hash(task, policy, agent1)
        hash2 = compute_execution_hash(task, policy, agent2)
        
        self.assertNotEqual(hash1, hash2)

if __name__ == '__main__':
    unittest.main()
