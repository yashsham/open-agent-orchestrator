import hashlib
import json
from typing import Any, Dict

def compute_execution_hash(task: str, policy: Any, agent: Any) -> str:
    """
    Compute a deterministic hash for an execution configuration.
    
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
        "tools": []
    }
    
    # Try to extract tools if available
    if hasattr(agent, "tools"):
        try:
            tools = getattr(agent, "tools")
            if isinstance(tools, (list, tuple)):
                for tool in tools:
                    agent_info["tools"].append({
                        "name": getattr(tool, "name", "Unknown"),
                        # We could include description/args here for stricter hash
                    })
        except Exception:
            # Fallback if tools access fails
            pass
    
    # 3. Construct canonical representation
    # Sort keys to ensure determinism
    data = {
        "task": task,
        "policy": policy_config,
        "agent": agent_info
    }
    
    # 4. Compute Hash
    # separators=(',', ':') removes whitespace for compactness and consistency
    serialized = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
