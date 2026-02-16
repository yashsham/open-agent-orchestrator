from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, List
from enum import Enum
import time
import uuid
import json
from datetime import datetime

from oao.runtime.hashing import compute_execution_hash


class ExecutionStatus(str, Enum):
    """Execution lifecycle status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    POLICY_VIOLATED = "POLICY_VIOLATED"

@dataclass(frozen=True)
class ExecutionSnapshot:
    """
    Immutable snapshot of the configuration for an execution.
    Once created, this should never change.
    
    frozen=True ensures immutability at the dataclass level.
    """
    task: str
    policy_config: tuple  # Changed from Dict to tuple for true immutability
    agent_config: tuple
    tool_config: tuple  # Changed from List to tuple
    runtime_version: str = "1.1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "task": self.task,
            "policy_config": dict(self.policy_config) if self.policy_config else {},
            "agent_config": dict(self.agent_config) if self.agent_config else {},
            "tool_config": list(self.tool_config) if self.tool_config else [],
            "runtime_version": self.runtime_version
        }

@dataclass
class Execution:
    """
    Canonical representation of an AI Agent Execution.
    
    This object is immutable after creation. All runtime state is derived
    from the event log, not stored in this object.
    """
    execution_id: str
    execution_hash: str
    snapshot: ExecutionSnapshot
    status: ExecutionStatus = ExecutionStatus.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    # NOTE: Runtime metrics (step_count, token_usage, tool_calls) are now
    # derived from the event log, not stored here. See event_store.py.
    
    @classmethod
    def create(cls, task: str, policy: any, agent: any, execution_id: Optional[str] = None) -> 'Execution':
        """
        Factory method to create a new Execution execution.
        """
        if not execution_id:
            execution_id = str(uuid.uuid4())

        # 1. Capture Policy Config (as immutable tuple of items)
        policy_config = ()
        if policy:
            config_dict = {
                k: v for k, v in policy.__dict__.items()
                if not k.startswith("_") and k != "start_time"
            }
            # Convert to sorted tuple of items for immutability
            policy_config = tuple(sorted(config_dict.items()))

        # 2. Capture Agent Config (as immutable tuple of items)
        agent_dict = {
            "class": agent.__class__.__name__,
            "name": getattr(agent, "name", "Unknown"),
        }
        agent_config = tuple(sorted(agent_dict.items()))

        # 3. Capture Tool Config (as immutable tuple)
        tool_list = []
        if hasattr(agent, "tools"):
            try:
                tools = getattr(agent, "tools")
                if isinstance(tools, (list, tuple)):
                    for tool in tools:
                        tool_list.append({
                            "name": getattr(tool, "name", "Unknown"),
                            "description": getattr(tool, "description", ""),
                        })
            except Exception:
                pass
        # Convert list to tuple for immutability
        tool_config = tuple(tool_list)

        # 4. create Snapshot
        snapshot = ExecutionSnapshot(
            task=task,
            policy_config=policy_config,
            agent_config=agent_config,
            tool_config=tool_config
        )

        # 5. Compute Deterministic Hash
        # We reuse the logic from hashing.py but apply it to our clean snapshot
        # For now, we can rely on internal hashing logic or call the helper.
        # Let's use the helper for consistency but ensure it aligns.
        # Actually, let's just re-implement robust hashing here for the snapshot.
        
        # We need a stable dict for hashing
        # Convert tuples back to dicts/lists for hashing consistency
        hash_data = {
            "task": snapshot.task,
            "policy": dict(snapshot.policy_config) if snapshot.policy_config else {},
            "agent": dict(snapshot.agent_config) if snapshot.agent_config else {},
            "tools": list(snapshot.tool_config) if snapshot.tool_config else [],
            "version": snapshot.runtime_version
        }
        
        # We use a custom compute here or the existing one?
        # The existing compute_execution_hash takes objects. 
        # Let's use compute_execution_hash since it's already tested, 
        # passing the raw objects.
        # BUT wait, we want the hash to be based on the SNAPSHOT, not the live objects
        # because the live objects might change (though unlikely during init).
        # It is safer to hash the snapshot.
        
        import hashlib
        serialized = json.dumps(hash_data, sort_keys=True, separators=(',', ':'), default=str)
        execution_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        return cls(
            execution_id=execution_id,
            execution_hash=execution_hash,
            snapshot=snapshot
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize execution to dictionary."""
        return {
            "execution_id": self.execution_id,
            "execution_hash": self.execution_hash,
            "snapshot": self.snapshot.to_dict(),
            "status": self.status.value if isinstance(self.status, ExecutionStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Execution':
        """Deserialize execution from dictionary."""
        snapshot_data = data.pop("snapshot")
        # Convert dicts/lists back to tuples for immutability
        snapshot = ExecutionSnapshot(
            task=snapshot_data["task"],
            policy_config=tuple(sorted(snapshot_data.get("policy_config", {}).items())),
            agent_config=tuple(sorted(snapshot_data.get("agent_config", {}).items())),
            tool_config=tuple(snapshot_data.get("tool_config", [])),
            runtime_version=snapshot_data.get("runtime_version", "1.1.0")
        )
        # Handle status enum
        status = data.get("status", "PENDING")
        if isinstance(status, str):
            status = ExecutionStatus(status)
        return cls(
            snapshot=snapshot,
            execution_id=data["execution_id"],
            execution_hash=data["execution_hash"],
            status=status,
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time())
        )
    
    def validate_hash(self) -> bool:
        """Verify that the execution hash matches the snapshot configuration."""
        snapshot_dict = self.snapshot.to_dict()
        expected_hash_data = {
            "task": snapshot_dict["task"],
            "policy": snapshot_dict["policy_config"],
            "agent": snapshot_dict["agent_config"],
            "tools": snapshot_dict["tool_config"],
            "version": snapshot_dict["runtime_version"]
        }
        serialized = json.dumps(expected_hash_data, sort_keys=True, separators=(',', ':'), default=str)
        import hashlib
        expected_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return self.execution_hash == expected_hash
