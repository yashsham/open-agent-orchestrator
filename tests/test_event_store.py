import unittest
import time
from oao.runtime.event_store import InMemoryEventStore, ExecutionState
from oao.runtime.events import ExecutionEvent, EventType


class TestEventStore(unittest.TestCase):
    
    def setUp(self):
        """Create a fresh event store for each test."""
        self.store = InMemoryEventStore()
        self.execution_id = "test-exec-123"
    
    def test_append_and_retrieve_single_event(self):
        """Test basic event append and retrieval."""
        event = ExecutionEvent(
            execution_id=self.execution_id,
            step_number=0,
            event_type=EventType.EXECUTION_STARTED,
            state="INIT"
        )
        
        self.store.append_event(self.execution_id, event)
        
        events = self.store.get_events(self.execution_id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].execution_id, self.execution_id)
        self.assertEqual(events[0].event_type, EventType.EXECUTION_STARTED)
    
    def test_event_ordering(self):
        """Test that events are retrieved in order by step_number."""
        # Add events out of order
        event2 = ExecutionEvent(
            execution_id=self.execution_id,
            step_number=2,
            event_type=EventType.STEP_COMPLETED
        )
        event0 = ExecutionEvent(
            execution_id=self.execution_id,
            step_number=0,
            event_type=EventType.EXECUTION_STARTED
        )
        event1 = ExecutionEvent(
            execution_id=self.execution_id,
            step_number=1,
            event_type=EventType.STEP_STARTED
        )
        
        self.store.append_event(self.execution_id, event2)
        self.store.append_event(self.execution_id, event0)
        self.store.append_event(self.execution_id, event1)
        
        # Should be returned in order
        events = self.store.get_events(self.execution_id)
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].step_number, 0)
        self.assertEqual(events[1].step_number, 1)
        self.assertEqual(events[2].step_number, 2)
    
    def test_range_query(self):
        """Test retrieving events in a specific step range."""
        for i in range(10):
            event = ExecutionEvent(
                execution_id=self.execution_id,
                step_number=i,
                event_type=EventType.STEP_COMPLETED
            )
            self.store.append_event(self.execution_id, event)
        
        # Get steps 3-6
        events = self.store.get_events(self.execution_id, from_step=3, to_step=6)
        self.assertEqual(len(events), 4)  # Steps 3, 4, 5, 6
        self.assertEqual(events[0].step_number, 3)
        self.assertEqual(events[-1].step_number, 6)
    
    def test_get_latest_event(self):
        """Test retrieving the most recent event."""
        event1 = ExecutionEvent(
            execution_id=self.execution_id,
            step_number=1,
            event_type=EventType.STEP_STARTED
        )
        event5 = ExecutionEvent(
            execution_id=self.execution_id,
            step_number=5,
            event_type=EventType.STEP_COMPLETED
        )
        
        self.store.append_event(self.execution_id, event1)
        self.store.append_event(self.execution_id, event5)
        
        latest = self.store.get_latest_event(self.execution_id)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.step_number, 5)
    
    def test_count_events(self):
        """Test event counting."""
        self.assertEqual(self.store.count_events(self.execution_id), 0)
        
        for i in range(5):
            event = ExecutionEvent(
                execution_id=self.execution_id,
                step_number=i,
                event_type=EventType.STEP_COMPLETED
            )
            self.store.append_event(self.execution_id, event)
        
        self.assertEqual(self.store.count_events(self.execution_id), 5)
    
    def test_replay_to_state(self):
        """Test state reconstruction from event log."""
        # Simulate a typical execution flow
        events = [
            ExecutionEvent(
                execution_id=self.execution_id,
                step_number=0,
                event_type=EventType.EXECUTION_STARTED,
                state="INIT",
                cumulative_tokens=0
            ),
            ExecutionEvent(
                execution_id=self.execution_id,
                step_number=1,
                event_type=EventType.STATE_ENTER,
                state="PLAN",
                cumulative_tokens=50,
                cumulative_tool_calls=0
            ),
            ExecutionEvent(
                execution_id=self.execution_id,
                step_number=2,
                event_type=EventType.STATE_ENTER,
                state="EXECUTE",
                cumulative_tokens=150,
                cumulative_tool_calls=2,
                output_data={"result": "success"}
            )
        ]
        
        for event in events:
            self.store.append_event(self.execution_id, event)
        
        # Replay to build state
        state = self.store.replay_to_state(self.execution_id)
        
        self.assertEqual(state.execution_id, self.execution_id)
        self.assertEqual(state.current_step, 2)
        self.assertEqual(state.current_state, "EXECUTE")
        self.assertEqual(state.cumulative_tokens, 150)
        self.assertEqual(state.cumulative_tool_calls, 2)
        self.assertIsNotNone(state.last_output)
        self.assertEqual(state.last_output["result"], "success")
    
    def test_replay_to_specific_step(self):
        """Test partial replay to a specific step."""
        for i in range(10):
            event = ExecutionEvent(
                execution_id=self.execution_id,
                step_number=i,
                event_type=EventType.STEP_COMPLETED,
                cumulative_tokens=i * 10
            )
            self.store.append_event(self.execution_id, event)
        
        # Replay only up to step 5
        state = self.store.replay_to_state(self.execution_id, target_step=5)
        
        self.assertEqual(state.current_step, 5)
        self.assertEqual(state.cumulative_tokens, 50)
    
    def test_invalid_event_validation(self):
        """Test that invalid events are rejected."""
        # Event with negative step number
        invalid_event = ExecutionEvent(
            execution_id=self.execution_id,
            step_number=-1,
            event_type=EventType.STEP_COMPLETED
        )
        
        with self.assertRaises(ValueError):
            self.store.append_event(self.execution_id, invalid_event)
    
    def test_get_execution_timeline(self):
        """Test timeline generation."""
        events = [
            ExecutionEvent(
                execution_id=self.execution_id,
                step_number=0,
                event_type=EventType.EXECUTION_STARTED,
                state="INIT"
            ),
            ExecutionEvent(
                execution_id=self.execution_id,
                step_number=1,
                event_type=EventType.STEP_COMPLETED,
                state="PLAN",
                cumulative_tokens=100
            )
        ]
        
        for event in events:
            self.store.append_event(self.execution_id, event)
        
        timeline = self.store.get_execution_timeline(self.execution_id)
        
        self.assertEqual(timeline["execution_id"], self.execution_id)
        self.assertEqual(timeline["total_events"], 2)
        self.assertEqual(len(timeline["events"]), 2)
        self.assertEqual(timeline["events"][0]["type"], "EXECUTION_STARTED")
        self.assertEqual(timeline["events"][1]["cumulative_tokens"], 100)


if __name__ == '__main__':
    unittest.main()
