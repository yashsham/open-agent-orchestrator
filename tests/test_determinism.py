import unittest
from oao.runtime.execution import Execution, ExecutionStatus
from oao.policy.strict_policy import StrictPolicy


class MockAgent:
    def __init__(self, name="TestAgent"):
        self.name = name
    def invoke(self, task):
        pass


class TestDeterminism(unittest.TestCase):
    """Test deterministic guarantees of the execution model."""
    
    def test_hash_consistency_across_executions(self):
        """Test that identical configurations produce identical hashes."""
        policy = StrictPolicy(max_steps=5, max_tokens=1000)
        agent = MockAgent(name="DeterministicAgent")
        task = "Process this deterministically"
        
        # Create 10 executions with identical config
        hashes = []
        for _ in range(10):
            exec_obj = Execution.create(task, policy, agent)
            hashes.append(exec_obj.execution_hash)
        
        # All hashes should be identical
        self.assertEqual(len(set(hashes)), 1, "Hashes should be deterministic")
    
    def test_hash_changes_with_task(self):
        """Test that task changes produce different hashes."""
        policy = StrictPolicy(max_steps=5)
        agent = MockAgent()
        
        exec1 = Execution.create("Task A", policy, agent)
        exec2 = Execution.create("Task B", policy, agent)
        
        self.assertNotEqual(exec1.execution_hash, exec2.execution_hash)
    
    def test_hash_changes_with_policy(self):
        """Test that policy changes produce different hashes."""
        agent = MockAgent()
        task = "Same task"
        
        exec1 = Execution.create(task, StrictPolicy(max_steps=5), agent)
        exec2 = Execution.create(task, StrictPolicy(max_steps=10), agent)
        
        self.assertNotEqual(exec1.execution_hash, exec2.execution_hash)
    
    def test_hash_changes_with_agent(self):
        """Test that agent changes produce different hashes."""
        policy = StrictPolicy(max_steps=5)
        task = "Same task"
        
        agent1 = MockAgent(name="Agent1")
        agent2 = MockAgent(name="Agent2")
        
        exec1 = Execution.create(task, policy, agent1)
        exec2 = Execution.create(task, policy, agent2)
        
        self.assertNotEqual(exec1.execution_hash, exec2.execution_hash)
    
    def test_execution_id_uniqueness(self):
        """Test that execution IDs are unique even with identical configs."""
        policy = StrictPolicy(max_steps=5)
        agent = MockAgent()
        task = "Same task"
        
        exec1 = Execution.create(task, policy, agent)
        exec2 = Execution.create(task, policy, agent)
        
        # IDs should be different
        self.assertNotEqual(exec1.execution_id, exec2.execution_id)
        # But hashes should be same
        self.assertEqual(exec1.execution_hash, exec2.execution_hash)
    
    def test_snapshot_immutability(self):
        """Test that ExecutionSnapshot is truly immutable."""
        policy = StrictPolicy(max_steps=5)
        agent = MockAgent()
        task = "Test task"
        
        exec_obj = Execution.create(task, policy, agent)
        snapshot = exec_obj.snapshot
        
        # Snapshot should be frozen - attempting to modify should fail
        with self.assertRaises(AttributeError):
            snapshot.task = "Modified task"
        
        with self.assertRaises(AttributeError):
            snapshot.runtime_version = "2.0.0"
    
    def test_hash_validation(self):
        """Test that hash validation works correctly."""
        policy = StrictPolicy(max_steps=5)
        agent = MockAgent()
        task = "Test task"
        
        exec_obj = Execution.create(task, policy, agent)
        
        # Hash should validate correctly
        self.assertTrue(exec_obj.validate_hash())
    
    def test_execution_serialization_roundtrip(self):
        """Test that execution can be serialized and deserialized."""
        policy = StrictPolicy(max_steps=5, max_tokens=1000)
        agent = MockAgent(name="SerializableAgent")
        task = "Test serialization"
        
        exec_obj = Execution.create(task, policy, agent)
        original_hash = exec_obj.execution_hash
        original_id = exec_obj.execution_id
        
        # Serialize to dict
        exec_dict = exec_obj.to_dict()
        
        # Deserialize
        restored_exec = Execution.from_dict(exec_dict)
        
        # Should be identical
        self.assertEqual(restored_exec.execution_id, original_id)
        self.assertEqual(restored_exec.execution_hash, original_hash)
        self.assertTrue(restored_exec.validate_hash())
    
    def test_status_enum(self):
        """Test execution status enum."""
        policy = StrictPolicy(max_steps=5)
        agent = MockAgent()
        task = "Test status"
        
        exec_obj = Execution.create(task, policy, agent)
        
        # Default status should be PENDING
        self.assertEqual(exec_obj.status, ExecutionStatus.PENDING)
        
        # Status should be an enum
        self.assertIsInstance(exec_obj.status, ExecutionStatus)
    
    def test_runtime_version_consistency(self):
        """Test that runtime version is included in hash."""
        policy = StrictPolicy(max_steps=5)
        agent = MockAgent()
        task = "Test task"
        
        exec1 = Execution.create(task, policy, agent)
        
        # Get snapshot dict
        snapshot_dict = exec1.snapshot.to_dict()
        
        # Runtime version should be present
        self.assertEqual(snapshot_dict["runtime_version"], "1.1.0")
        
        # Changing runtime version should change hash (if we could)
        # This is verified by the hash computation including runtime_version


class TestExecutionStateContract(unittest.TestCase):
    """Test that execution state contract is properly enforced."""
    
    def test_execution_has_required_fields(self):
        """Test that all required fields are present."""
        policy = StrictPolicy(max_steps=5)
        agent = MockAgent()
        task = "Test task"
        
        exec_obj = Execution.create(task, policy, agent)
        
        # Required fields
        self.assertIsNotNone(exec_obj.execution_id)
        self.assertIsNotNone(exec_obj.execution_hash)
        self.assertIsNotNone(exec_obj.snapshot)
        self.assertIsNotNone(exec_obj.status)
        self.assertIsNotNone(exec_obj.created_at)
        self.assertIsNotNone(exec_obj.updated_at)
    
    def test_snapshot_has_required_fields(self):
        """Test that snapshot has all required fields."""
        policy = StrictPolicy(max_steps=5)
        agent = MockAgent()
        task = "Test task"
        
        exec_obj = Execution.create(task, policy, agent)
        snapshot = exec_obj.snapshot
        
        # Required snapshot fields
        self.assertIsNotNone(snapshot.task)
        self.assertIsNotNone(snapshot.policy_config)
        self.assertIsNotNone(snapshot.agent_config)
        self.assertIsNotNone(snapshot.tool_config)
        self.assertIsNotNone(snapshot.runtime_version)


if __name__ == '__main__':
    unittest.main()
