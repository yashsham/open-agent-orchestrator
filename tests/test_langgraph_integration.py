import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import asyncio

# Mock langgraph module before importing adapter
mock_langgraph = MagicMock()
sys.modules["langgraph"] = mock_langgraph

from oao.adapters.langgraph_adapter import LangGraphAdapter

class TestLangGraphIntegration(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.mock_graph = MagicMock()
        self.adapter = LangGraphAdapter(self.mock_graph)

    def test_execute_string_task(self):
        # Setup
        task = "hello world"
        self.mock_graph.invoke.return_value = {"messages": ["response"]}
        
        # Execute
        # Patch where OAOCallbackHandler is used/imported. 
        # It is imported inside the method, so we can patch the source module.
        with patch('oao.adapters.langchain.callbacks.OAOCallbackHandler') as MockCallback:
            result = self.adapter.execute(task)
            
            # Verify input construction
            expected_input = {"messages": [{"role": "user", "content": task}]}
            self.mock_graph.invoke.assert_called_once()
            args, kwargs = self.mock_graph.invoke.call_args
            self.assertEqual(args[0], expected_input)
            
            # Verify callback injection
            self.assertIn("config", kwargs)
            self.assertIn("callbacks", kwargs["config"])
            # Validate that our mock callback was used
            # Since MockCallback is a class, calling it returns an instance.
            # The code does callback = OAOCallbackHandler(event_bus)
            # So kwargs["config"]["callbacks"][0] should be MockCallback.return_value
            self.assertEqual(kwargs["config"]["callbacks"][0], MockCallback.return_value)

    def test_execute_dict_task(self):
        # Setup
        task = {"custom": "input"}
        self.mock_graph.invoke.return_value = {"out": "put"}
        
        # Execute
        # We need to patch callback handler here too or it will try to import real one which might fail if dependencies missing
        # but oao.adapters.langchain.callbacks imports logic that might require langchain.
        # So safe to patch it.
        with patch('oao.adapters.langchain.callbacks.OAOCallbackHandler'):
            self.adapter.execute(task)
        
        # Verify passed through
        self.mock_graph.invoke.assert_called_once()
        args, _ = self.mock_graph.invoke.call_args
        self.assertEqual(args[0], task)

    async def test_execute_async(self):
        # Setup
        self.mock_graph.ainvoke = AsyncMock(return_value={"out": "put"})
        task = "async test"
        
        # Execute
        with patch('oao.adapters.langchain.callbacks.OAOCallbackHandler'):
            result = await self.adapter.execute_async(task)
            
            # Verify
            self.mock_graph.ainvoke.assert_called_once()
            args, _ = self.mock_graph.ainvoke.call_args
            self.assertEqual(args[0], {"messages": [{"role": "user", "content": task}]})

    def test_import_error(self):
         pass
