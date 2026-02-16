from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import time

from oao.runtime.events import ExecutionEvent, EventType


@dataclass
class ExecutionState:
    """
    Reconstructed state from event log.
    This is the source of truth for runtime metrics.
    """
    execution_id: str
    current_step: int = 0
    cumulative_tokens: int = 0
    cumulative_tool_calls: int = 0
    current_state: Optional[str] = None
    last_output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class EventStore(ABC):
    """
    Abstract event store for append-only event persistence.
    
    This is the foundation of the event-sourced architecture.
    All implementations must guarantee:
    - Append-only writes
    - Event ordering preservation
    - Efficient range queries
    """
    
    @abstractmethod
    def append_event(self, execution_id: str, event: ExecutionEvent) -> None:
        """
        Append an event to the execution log.
        
        Args:
            execution_id: Unique execution identifier
            event: Event to append (must be validated)
        """
        pass
    
    @abstractmethod
    def get_events(
        self, 
        execution_id: str, 
        from_step: int = 0,
        to_step: Optional[int] = None
    ) -> List[ExecutionEvent]:
        """
        Retrieve events for an execution in order.
        
        Args:
            execution_id: Unique execution identifier
            from_step: Starting step number (inclusive)
            to_step: Ending step number (inclusive), None = all
            
        Returns:
            List of events ordered by step_number ascending
        """
        pass
    
    @abstractmethod
    def get_latest_event(self, execution_id: str) -> Optional[ExecutionEvent]:
        """Get the most recent event for an execution."""
        pass
    
    @abstractmethod
    def count_events(self, execution_id: str) -> int:
        """Count total events for an execution."""
        pass
    
    def replay_to_state(
        self, 
        execution_id: str, 
        target_step: Optional[int] = None
    ) -> ExecutionState:
        """
        Reconstruct execution state from event log.
        
        This is the core replay mechanism. It rebuilds state by
        replaying all events up to target_step.
        
        Args:
            execution_id: Unique execution identifier
            target_step: Stop replay at this step, None = replay all
            
        Returns:
            ExecutionState reconstructed from events
        """
        events = self.get_events(execution_id, from_step=0, to_step=target_step)
        
        state = ExecutionState(execution_id=execution_id)
        
        for event in events:
            # Update cumulative metrics from event
            state.cumulative_tokens = event.cumulative_tokens or 0
            state.cumulative_tool_calls = event.cumulative_tool_calls or 0
            state.current_step = event.step_number
            
            # Track state transitions
            if event.event_type == EventType.STATE_ENTER:
                state.current_state = event.state
            
            # Track outputs
            if event.output_data:
                state.last_output = event.output_data
            
            # Track errors
            if event.error:
                state.error = event.error
        
        return state
    
    def get_execution_timeline(self, execution_id: str) -> Dict[str, Any]:
        """
        Generate a timeline view of the execution.
        
        This is useful for debugging and visualization.
        """
        events = self.get_events(execution_id)
        
        timeline = {
            "execution_id": execution_id,
            "total_events": len(events),
            "events": []
        }
        
        # Derive status
        status = "PENDING"
        if events:
            last_event = events[-1]
            if last_event.event_type == EventType.EXECUTION_COMPLETED:
                status = "COMPLETED"
            elif last_event.event_type == EventType.EXECUTION_FAILED:
                status = "FAILED"
            elif last_event.event_type == EventType.POLICY_VIOLATION:
                status = "POLICY_VIOLATION"
            else:
                status = "RUNNING"
                
        timeline["status"] = status
        
        for event in events:
            timeline["events"].append({
                "step": event.step_number,
                "type": event.event_type.value,
                "timestamp": event.timestamp,
                "state": event.state,
                "cumulative_tokens": event.cumulative_tokens,
                "error": event.error
            })
        
        return timeline


class RedisEventStore(EventStore):
    """
    Redis-backed event store implementation.
    
    Uses Redis sorted sets for efficient event ordering and range queries.
    Events are stored as JSON-serialized strings.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        import redis
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    def append_event(self, execution_id: str, event: ExecutionEvent) -> None:
        """Append event to Redis sorted set."""
        if not event.validate():
            raise ValueError(f"Invalid event: {event}")
        
        key = f"oao:events:{execution_id}"
        
        # Use step_number as score for ordering
        import json
        event_json = json.dumps(event.to_dict(), default=str)
        
        # ZADD adds to sorted set with score = step_number
        self.redis.zadd(key, {event_json: event.step_number})
        
        # Set retention (7 days)
        self.redis.expire(key, 604800)
        
        # Also append to list for fast sequential access
        list_key = f"{key}:list"
        self.redis.rpush(list_key, event_json)
        self.redis.expire(list_key, 604800)
    
    def get_events(
        self, 
        execution_id: str, 
        from_step: int = 0,
        to_step: Optional[int] = None
    ) -> List[ExecutionEvent]:
        """Retrieve events from Redis sorted set."""
        key = f"oao:events:{execution_id}"
        
        import json
        
        if to_step is None:
            # Get all events from from_step onwards
            event_strings = self.redis.zrangebyscore(key, from_step, '+inf')
        else:
            # Get events in range
            event_strings = self.redis.zrangebyscore(key, from_step, to_step)
        
        events = []
        for event_str in event_strings:
            event_dict = json.loads(event_str)
            events.append(ExecutionEvent.from_dict(event_dict))
        
        return events
    
    def get_latest_event(self, execution_id: str) -> Optional[ExecutionEvent]:
        """Get the most recent event."""
        key = f"oao:events:{execution_id}"
        
        import json
        
        # Get highest scoring member (most recent step)
        event_strings = self.redis.zrevrange(key, 0, 0)
        
        if not event_strings:
            return None
        
        event_dict = json.loads(event_strings[0])
        return ExecutionEvent.from_dict(event_dict)
    
    def count_events(self, execution_id: str) -> int:
        """Count total events."""
        key = f"oao:events:{execution_id}"
        return self.redis.zcard(key)


class InMemoryEventStore(EventStore):
    """
    In-memory event store for testing.
    
    Not suitable for production use - no persistence.
    """
    
    def __init__(self):
        # Dict[execution_id, List[ExecutionEvent]]
        self._events: Dict[str, List[ExecutionEvent]] = {}
    
    def append_event(self, execution_id: str, event: ExecutionEvent) -> None:
        """Append event to in-memory list."""
        if not event.validate():
            raise ValueError(f"Invalid event: {event}")
        
        if execution_id not in self._events:
            self._events[execution_id] = []
        
        self._events[execution_id].append(event)
        
        # Keep sorted by step_number
        self._events[execution_id].sort(key=lambda e: e.step_number)
    
    def get_events(
        self, 
        execution_id: str, 
        from_step: int = 0,
        to_step: Optional[int] = None
    ) -> List[ExecutionEvent]:
        """Retrieve events from in-memory storage."""
        if execution_id not in self._events:
            return []
        
        all_events = self._events[execution_id]
        
        # Filter by step range
        filtered = [
            e for e in all_events
            if e.step_number >= from_step and (to_step is None or e.step_number <= to_step)
        ]
        
        return filtered
    
    def get_latest_event(self, execution_id: str) -> Optional[ExecutionEvent]:
        """Get the most recent event."""
        if execution_id not in self._events:
            return None
        
        events = self._events[execution_id]
        return events[-1] if events else None
    
    def count_events(self, execution_id: str) -> int:
        """Count total events."""
        if execution_id not in self._events:
            return 0
        return len(self._events[execution_id])
