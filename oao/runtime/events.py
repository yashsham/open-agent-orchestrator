from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import time


class EventType(str, Enum):
    # Execution Lifecycle Events
    EXECUTION_STARTED = "EXECUTION_STARTED"
    EXECUTION_COMPLETED = "EXECUTION_COMPLETED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    
    # Step Lifecycle Events
    STEP_STARTED = "STEP_STARTED"
    STEP_COMPLETED = "STEP_COMPLETED"
    STEP_FAILED = "STEP_FAILED"
    
    # State Transitions
    STATE_ENTER = "STATE_ENTER"
    STATE_EXIT = "STATE_EXIT"
    
    # Operation Events
    TOOL_CALL = "TOOL_CALL"
    TOOL_CALL_SUCCESS = "TOOL_CALL_SUCCESS"
    TOOL_CALL_FAILED = "TOOL_CALL_FAILED"
    IDEMPOTENT_TOOL_SKIPPED = "IDEMPOTENT_TOOL_SKIPPED"
    
    # Policy Events
    POLICY_VIOLATION = "POLICY_VIOLATION"
    TOKEN_BUDGET_EXCEEDED = "TOKEN_BUDGET_EXCEEDED"
    MAX_STEPS_EXCEEDED = "MAX_STEPS_EXCEEDED"
    TIMEOUT_EXCEEDED = "TIMEOUT_EXCEEDED"
    
    # Retry Events
    RETRY_ATTEMPTED = "RETRY_ATTEMPTED"
    
    # General Events
    ERROR = "ERROR"
    
    # Legacy aliases for backward compatibility
    workflow_started = "EXECUTION_STARTED"
    workflow_completed = "EXECUTION_COMPLETED"


@dataclass
class ExecutionEvent:
    """
    Canonical Event for OAO Event-Sourced Architecture.
    Represents an atomic state transition or significant action.
    
    All runtime state is derived from the event log, not mutable state.
    Events are append-only and never mutated.
    """
    execution_id: str
    step_number: int
    event_type: EventType
    timestamp: float = field(default_factory=time.time)
    
    # Payload details
    state: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None  # Renamed from 'input' to avoid keyword conflict
    output_data: Optional[Dict[str, Any]] = None  # Renamed from 'output'
    error: Optional[str] = None
    
    # Cumulative metrics (sum of all previous events)
    cumulative_tokens: Optional[int] = 0
    cumulative_steps: Optional[int] = 0
    cumulative_tool_calls: int = 0
    
    # Trace Context
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    
    # Step-specific metrics (delta for this step)
    step_tokens: Optional[int] = 0
    tool_calls: Optional[List[Dict[str, Any]]] = None
    
    # Replay metadata
    is_replay: bool = False
    original_execution_id: Optional[str] = None
    replay_from_step: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary for persistence."""
        return {
            "execution_id": self.execution_id,
            "step_number": self.step_number,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "state": self.state,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error": self.error,
            "cumulative_tokens": self.cumulative_tokens,
            "cumulative_steps": self.cumulative_steps,
            "cumulative_tool_calls": self.cumulative_tool_calls,
            "step_tokens": self.step_tokens,
            "tool_calls": self.tool_calls,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "is_replay": self.is_replay,
            "original_execution_id": self.original_execution_id,
            "replay_from_step": self.replay_from_step
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionEvent':
        """Deserialize event from dictionary."""
        # Handle event_type enum
        event_type = data.get("event_type")
        if isinstance(event_type, str):
            event_type = EventType(event_type)
        
        return cls(
            execution_id=data["execution_id"],
            step_number=data["step_number"],
            event_type=event_type,
            timestamp=data.get("timestamp", time.time()),
            state=data.get("state"),
            input_data=data.get("input_data"),
            output_data=data.get("output_data"),
            error=data.get("error"),
            cumulative_tokens=data.get("cumulative_tokens", 0),
            cumulative_steps=data.get("cumulative_steps", 0),
            cumulative_tool_calls=data.get("cumulative_tool_calls", 0),
            step_tokens=data.get("step_tokens", 0),
            tool_calls=data.get("tool_calls"),
            trace_id=data.get("trace_id"),
            span_id=data.get("span_id"),
            is_replay=data.get("is_replay", False),
            original_execution_id=data.get("original_execution_id"),
            replay_from_step=data.get("replay_from_step")
        )
    
    def validate(self) -> bool:
        """Validate that required fields are present."""
        if not self.execution_id:
            return False
        if self.step_number < 0:
            return False
        if not isinstance(self.event_type, EventType):
            return False
        return True

# Legacy Event Wrapper for backward compatibility during refactor
class Event:
    def __init__(self, event_type: EventType, payload: Dict[str, Any]):
        self.event_type = event_type
        self.payload = payload


class GlobalEventRegistry:
    """
    Registry for global event listeners.
    """
    _listeners: Dict[EventType, list] = {}

    @classmethod
    def register(cls, event_type: EventType, listener):
        if event_type not in cls._listeners:
            cls._listeners[event_type] = []
        cls._listeners[event_type].append(listener)

    @classmethod
    def get_listeners(cls, event_type: EventType):
        return cls._listeners.get(event_type, [])


