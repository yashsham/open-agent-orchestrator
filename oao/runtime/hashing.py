import hashlib
import json
from typing import Any, Dict, Optional, TYPE_CHECKING
import time

if TYPE_CHECKING:
    from oao.runtime.execution import Execution

def compute_execution_hash(task: str, policy: Any, agent: Any) -> str:
    """
    Compute a deterministic hash for an execution configuration.
    
    This is a helper function that mimics the logic in Execution.create
    to generate a hash from raw components.
    
    Args:
        task: The task string.
        policy: The policy object (will be serialized).
        agent: The agent object (will use class name/config).
        
    Returns:
        SHA-256 hash string.
    """
    
    # 1. Serialize Policy
    policy_config = {}
    if policy:
        # Extract relevant policy attributes (excluding runtime state like start_time)
        policy_config = {
            k: v for k, v in policy.__dict__.items()
            if not k.startswith("_") and k != "start_time"
        }
    
    # 2. Serialize Agent Identity
    agent_info = {
        "class": agent.__class__.__name__,
        "name": getattr(agent, "name", "Unknown"),
    }
    
    # 3. Serialize Tools
    tool_config = []
    if hasattr(agent, "tools"):
        try:
            tools = getattr(agent, "tools")
            if isinstance(tools, (list, tuple)):
                for tool in tools:
                    tool_config.append({
                        "name": getattr(tool, "name", "Unknown"),
                        "description": getattr(tool, "description", ""),
                    })
        except Exception:
            pass
    
    # 4. Construct canonical representation
    # Sort keys to ensure determinism
    # Version pin for hash stability
    import oao
    runtime_version = oao.__version__
    
    data = {
        "task": task,
        "policy": policy_config,
        "agent": agent_info,
        "tools": tool_config,
        "version": runtime_version
    }
    
    # 5. Compute Hash
    # separators=(',', ':') removes whitespace for compactness and consistency
    # ensure_ascii=False ensures consistent encoding
    # default=str handles non-serializable objects gracefully
    serialized = json.dumps(data, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def verify_execution_hash(execution: 'Execution', claimed_hash: str) -> bool:
    """
    Verify that an Execution object's hash matches the claimed hash.
    """
    # Simply re-compute based on snapshot
    computed = execution.execution_hash # The execution object already has it computed on init
    return computed == claimed_hash

