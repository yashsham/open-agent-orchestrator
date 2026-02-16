from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
import redis
import time
from datetime import datetime

class PersistenceAdapter(ABC):
    """Abstract base class for workflow persistence."""
    
    @abstractmethod
    def save_workflow_state(self, workflow_id: str, state: Dict[str, Any]):
        """Save overall workflow state."""
        pass

    @abstractmethod
    def save_node_state(self, workflow_id: str, node_name: str, state: Dict[str, Any]):
        """Save the state of a specific node."""
        pass

    @abstractmethod
    def load_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Load workflow metadata."""
        pass

    @abstractmethod
    def load_node_state(self, workflow_id: str, node_name: str) -> Optional[Dict[str, Any]]:
        """Load the state of a specific node."""
        pass
    
    @abstractmethod
    def load_all_nodes(self, workflow_id: str) -> Dict[str, Dict[str, Any]]:
        """Load states of all nodes in a workflow."""
        pass


class RedisPersistenceAdapter(PersistenceAdapter):
    """Redis-backed persistence for DAG execution."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis = redis.from_url(redis_url, decode_responses=True)

    def save_workflow_state(self, workflow_id: str, state: Dict[str, Any]):
        key = f"oao_workflow:{workflow_id}"
        # Ensure timestamps are strings
        if "created_at" not in state:
            state["created_at"] = datetime.utcnow().isoformat()
        state["updated_at"] = datetime.utcnow().isoformat()
        
        # Redis HSET requires flat mapping or string values. We'll store as JSON for simplicity in 'data' field
        # or flat fields if simple. Let's use flat fields for status.
        mapping = {k: str(v) for k, v in state.items()}
        self.redis.hset(key, mapping=mapping)
        self.redis.expire(key, 86400) # 24h retention

    def save_node_state(self, workflow_id: str, node_name: str, state: Dict[str, Any]):
        key = f"oao_workflow_nodes:{workflow_id}"
        # Store as JSON string in the hash map where field=node_name
        self.redis.hset(key, node_name, json.dumps(state))
        self.redis.expire(key, 86400)

    def load_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        key = f"oao_workflow:{workflow_id}"
        data = self.redis.hgetall(key)
        return data if data else None

    def load_node_state(self, workflow_id: str, node_name: str) -> Optional[Dict[str, Any]]:
        key = f"oao_workflow_nodes:{workflow_id}"
        data = self.redis.hget(key, node_name)
        return json.loads(data) if data else None

    def load_all_nodes(self, workflow_id: str) -> Dict[str, Dict[str, Any]]:
        key = f"oao_workflow_nodes:{workflow_id}"
        data = self.redis.hgetall(key)
        # Convert all JSON string values to dicts
        return {k: json.loads(v) for k, v in data.items()}

    def save_execution_step(self, execution_id: str, step_number: int, state: Dict[str, Any]):
        """Save a snapshot of execution state at a specific step."""
        key = f"oao_execution:{execution_id}:steps"
        
        # Filter out non-serializable objects (agent, adapter)
        # We only want to persist data: inputs, outputs, metrics, plan
        safe_state = {
            k: v for k, v in state.items() 
            if k not in ["agent", "adapter"] 
            and isinstance(v, (str, int, float, bool, list, dict, type(None)))
        }
        
        # Store comprehensive state snapshot
        snapshot = {
            "step_number": step_number,
            "timestamp": datetime.utcnow().isoformat(),
            "state": safe_state
        }
        # Use json.dumps with default=str for any other edge cases
        self.redis.zadd(key, {json.dumps(snapshot, default=str): step_number})
        self.redis.expire(key, 604800) # 7 days retention for history

    def get_execution_history(self, execution_id: str) -> list[Dict[str, Any]]:
        """Get full history of an execution."""
        key = f"oao_execution:{execution_id}:steps"
        # Get all steps sorted by score (step number)
        steps = self.redis.zrange(key, 0, -1)
        return [json.loads(s) for s in steps]

    def get_execution_step(self, execution_id: str, step_number: int) -> Optional[Dict[str, Any]]:
        """Get state at a specific step."""
        key = f"oao_execution:{execution_id}:steps"
        # Get specific range by score
        steps = self.redis.zrangebyscore(key, step_number, step_number)
        return json.loads(steps[0]) if steps else None

    # =====================================================
    # Crash Recovery Support
    # =====================================================

    def register_active_execution(self, execution_id: str):
        """Mark an execution as active (running)."""
        self.redis.sadd("oao:active_executions", execution_id)

    def remove_active_execution(self, execution_id: str):
        """Mark an execution as completed and remove from active set."""
        self.redis.srem("oao:active_executions", execution_id)

    def list_active_executions(self) -> list[str]:
        """List all currently active execution IDs."""
        return list(self.redis.smembers("oao:active_executions"))

    def save_execution_spec(self, execution_id: str, spec: Dict[str, Any]):
        """Save the execution specification (config) for recovery."""
        key = f"oao_execution:{execution_id}:spec"
        self.redis.set(key, json.dumps(spec))
        self.redis.expire(key, 604800) # 7 days

    def load_execution_spec(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Load the execution specification."""
        key = f"oao_execution:{execution_id}:spec"
        data = self.redis.get(key)
        return json.loads(data) if data else None

    def append_event(self, execution_id: str, event: Dict[str, Any]):
        """Append an event to the execution log."""
        key = f"oao_execution:{execution_id}:events"
        # Use RPUSH to append to list
        self.redis.rpush(key, json.dumps(event, default=str))
        self.redis.expire(key, 604800)

    def get_execution_events(self, execution_id: str) -> list[Dict[str, Any]]:
        """Get all events for an execution."""
        key = f"oao_execution:{execution_id}:events"
        events = self.redis.lrange(key, 0, -1)
        return [json.loads(e) for e in events]
        
    def increment_recovery_count(self, execution_id: str) -> int:
        """Increment and return the number of recovery attempts."""
        key = f"oao_execution:{execution_id}:recovery_count"
        count = self.redis.incr(key)
        self.redis.expire(key, 604800) # 7 days
        return count
        
    def get_recovery_count(self, execution_id: str) -> int:
        """Get the current number of recovery attempts."""
        key = f"oao_execution:{execution_id}:recovery_count"
        count = self.redis.get(key)
        return int(count) if count else 0


class InMemoryPersistenceAdapter(PersistenceAdapter):
    """In-memory persistence for testing and benchmarking."""
    
    def __init__(self):
        self.workflows = {}
        self.nodes = {}
        self.steps = {}
        self.specs = {}
        self.active_executions = set()
        self.events = {}
        self.recovery_counts = {}

    def save_workflow_state(self, workflow_id: str, state: Dict[str, Any]):
        self.workflows[workflow_id] = state

    def save_node_state(self, workflow_id: str, node_name: str, state: Dict[str, Any]):
        if workflow_id not in self.nodes:
            self.nodes[workflow_id] = {}
        self.nodes[workflow_id][node_name] = state

    def load_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        return self.workflows.get(workflow_id)

    def load_node_state(self, workflow_id: str, node_name: str) -> Optional[Dict[str, Any]]:
        return self.nodes.get(workflow_id, {}).get(node_name)

    def load_all_nodes(self, workflow_id: str) -> Dict[str, Dict[str, Any]]:
        return self.nodes.get(workflow_id, {})

    def save_execution_step(self, execution_id: str, step_number: int, state: Dict[str, Any]):
        if execution_id not in self.steps:
            self.steps[execution_id] = []
        
        safe_state = {
            k: v for k, v in state.items() 
            if k not in ["agent", "adapter", "event_store"] 
            and isinstance(v, (str, int, float, bool, list, dict, type(None)))
        }
        
        snapshot = {
            "step_number": step_number,
            "timestamp": datetime.utcnow().isoformat(),
            "state": safe_state
        }
        self.steps[execution_id].append(snapshot)
        self.steps[execution_id].sort(key=lambda x: x["step_number"])

    def get_execution_history(self, execution_id: str) -> list[Dict[str, Any]]:
        return self.steps.get(execution_id, [])

    def get_execution_step(self, execution_id: str, step_number: int) -> Optional[Dict[str, Any]]:
        steps = self.steps.get(execution_id, [])
        for s in steps:
            if s["step_number"] == step_number:
                return s
        return None

    def register_active_execution(self, execution_id: str):
        self.active_executions.add(execution_id)

    def remove_active_execution(self, execution_id: str):
        self.active_executions.discard(execution_id)

    def list_active_executions(self) -> list[str]:
        return list(self.active_executions)

    def save_execution_spec(self, execution_id: str, spec: Dict[str, Any]):
        self.specs[execution_id] = spec

    def load_execution_spec(self, execution_id: str) -> Optional[Dict[str, Any]]:
        return self.specs.get(execution_id)

    def append_event(self, execution_id: str, event: Dict[str, Any]):
        if execution_id not in self.events:
            self.events[execution_id] = []
        self.events[execution_id].append(event)

    def get_execution_events(self, execution_id: str) -> list[Dict[str, Any]]:
        return self.events.get(execution_id, [])

    def increment_recovery_count(self, execution_id: str) -> int:
        count = self.recovery_counts.get(execution_id, 0) + 1
        self.recovery_counts[execution_id] = count
        return count

    def get_recovery_count(self, execution_id: str) -> int:
        return self.recovery_counts.get(execution_id, 0)


