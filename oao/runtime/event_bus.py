from typing import Callable, Dict, List

from oao.runtime.events import Event, EventType


class EventBus:
    """
    Central event dispatcher.
    """

    def __init__(self):
        self._listeners: Dict[EventType, List[Callable]] = {}

    def register(self, event_type: EventType, handler: Callable):
        if event_type not in self._listeners:
            self._listeners[event_type] = []

        self._listeners[event_type].append(handler)

    def emit(self, event: Event):
        handlers = self._listeners.get(event.event_type, [])

        for handler in handlers:
            handler(event)
