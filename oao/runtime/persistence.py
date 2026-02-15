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
