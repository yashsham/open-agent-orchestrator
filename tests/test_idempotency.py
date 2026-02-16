import unittest
import asyncio
from typing import Any
from oao.runtime.orchestrator import Orchestrator
from oao.runtime.event_store import InMemoryEventStore
from oao.runtime.events import EventType
from oao.runtime.persistence import RedisPersistenceAdapter
from unittest.mock import MagicMock

class IdempotentAgent:
    def __init__(self):
        self.call_count = 0
        self.tools = [self.side_effect_tool]

    def side_effect_tool(self, input_str: str):
        self.call_count += 1
        return f"Processed {input_str}"

    def plan(self, task: str): return task
    
    def invoke(self, task: str, config=None):
        # Simulate a tool call through the adapter (which will use wrap_tool)
        # In a real scenario, the adapter handles this. 
        # For this test, we'll verify the wrapper directly if needed, 
        # or run through the orchestrator.
        return self.side_effect_tool(task)

class TestIdempotency(unittest.IsolatedAsyncioTestCase):
    async def test_tool_idempotency(self):
        from oao.runtime.tool_wrapper import wrap_tool
        
        event_store = InMemoryEventStore()
        context = {
            "execution_id": "test_exec_1",
            "event_store": event_store,
            "tool_calls": 0,
            "step_count": 1
        }
        
        def real_tool(x):
            return x * 2
            
        wrapped = wrap_tool("double", real_tool, context, None)
        
        # First call
        res1 = wrapped(5)
        self.assertEqual(res1, 10)
        self.assertEqual(context["tool_calls"], 1)
        
        # Verify event was stored
        events = event_store.get_events("test_exec_1")
        self.assertTrue(any(e.event_type == EventType.TOOL_CALL_SUCCESS for e in events))
        
        # Second call with SAME arguments
        res2 = wrapped(5)
        self.assertEqual(res2, 10)
        self.assertEqual(context["tool_calls"], 1) # Should NOT increment
        
        # Third call with DIFFERENT arguments
        res3 = wrapped(10)
        self.assertEqual(res3, 20)
        self.assertEqual(context["tool_calls"], 2) # Should increment

if __name__ == "__main__":
    unittest.main()
