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

