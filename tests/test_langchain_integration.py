import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from oao.runtime.events import EventType

# Mock imports for LangChain to safely test without it installed if necessary
# But real testing requires it. We assume dev environment has it.
try:
    from langchain_core.messages import HumanMessage, AIMessage
except ImportError:
    pass

from oao.adapters.langchain_adapter import LangChainAdapter

class TestLangChainIntegration(unittest.TestCase):
    
    def test_callback_event_emission(self):
        # Mock Agent
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"output": "hello"}
        
        # We need to splice the import inside the method or patch where it's defined
        # Since imports are inside methods in LangChainAdapter, we can't easily patch them via module attribute
        # unless we patch 'sys.modules' or similar.
        # EASIER: Patch the module where EventBus comes from, but targeting the adapter file is tricky if it's not global.
        # Actually, if we patch 'oao.runtime.event_bus.EventBus', it should work if we patch it BEFORE the method is called.
        
        with patch('oao.runtime.event_bus.EventBus') as MockEventBus:
            adapter = LangChainAdapter(mock_agent)
            
            # Execute
            adapter.execute("test task")
            
            # Verify EventBus was initialized
            MockEventBus.assert_called()
            event_bus_instance = MockEventBus.return_value
            
            args, kwargs = mock_agent.invoke.call_args
            self.assertIn("config", kwargs)
            self.assertIn("callbacks", kwargs["config"])
            # Validate callback presence. Internal details depend on OAOCallbackHandler implementation
            # We assume it uses the passed event bus.

    def test_memory_integration(self):
        # Patch classes where they are imported
        # Since they are imported inside __init__, we need to patch before instantiating adapter
        # But wait, they are imported from modules.
        
        with patch('oao.adapters.langchain.memory.OAORedisChatMessageHistory') as MockHistory, \
             patch('langchain_core.runnables.history.RunnableWithMessageHistory') as MockRunnable:
            
            mock_agent = MagicMock()
            session_id = "test-session"
            
            # We need to make sure the imports inside __init__ find our mocks.
            # Patching the source modules usually works even for local imports if done right.
            
            # However, if the module is not yet imported, we might need to mock sys.modules or use patch.dict
            # Let's try patching the source locations.
            
            adapter = LangChainAdapter(mock_agent, session_id=session_id)
            
            # Verify RunnableWithMessageHistory wrapped the agent
            MockRunnable.assert_called()
            self.assertIsNotNone(adapter.agent_with_history)
            
            # Verify execution uses the wrapped agent
            adapter.execute("test task")
            
            MockRunnable.return_value.invoke.assert_called()
            args, kwargs = MockRunnable.return_value.invoke.call_args
            self.assertEqual(kwargs["config"]["configurable"]["session_id"], session_id)

    def test_memory_persistence_logic(self):
        # Test OAORedisChatMessageHistory directly
        from oao.adapters.langchain.memory import OAORedisChatMessageHistory
        
        with patch('oao.adapters.langchain.memory.RedisPersistenceAdapter') as MockPersistence:
            mock_redis = MockPersistence.return_value.redis
            mock_redis.lrange.return_value = [
                b'{"type": "human", "data": {"content": "hi"}}',
                b'{"type": "ai", "data": {"content": "hello"}}'
            ]
            
            history = OAORedisChatMessageHistory("session-123")
            messages = history.messages
            
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0].content, "hi")
            self.assertEqual(messages[1].content, "hello")
            
            # Test add_message
            history.add_message(messages[0])
            mock_redis.rpush.assert_called()
