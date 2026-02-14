from enum import Enum
from typing import Dict, Any


class EventType(str, Enum):
    STATE_ENTER = "STATE_ENTER"
    TOOL_CALL = "TOOL_CALL"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    EXECUTION_COMPLETE = "EXECUTION_COMPLETE"


class Event:
    def __init__(self, event_type: EventType, payload: Dict[str, Any]):
        self.event_type = event_type
        self.payload = payload
