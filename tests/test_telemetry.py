import unittest
from unittest.mock import MagicMock, patch
import asyncio
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from oao.runtime.tool_wrapper import wrap_tool
from oao.runtime.orchestrator import Orchestrator
from oao.runtime.state_machine import AgentState
from oao.protocol.report import ExecutionReport

class TestTelemetry(unittest.TestCase):
    def setUp(self):
        self.exporter = InMemorySpanExporter()
        self.provider = TracerProvider()
        processor = SimpleSpanProcessor(self.exporter)
        self.provider.add_span_processor(processor)
        self.tracer = self.provider.get_tracer("test_tracer")
        
    def test_tool_span(self):
        context = {"tool_calls": 0}
        def my_tool(x):
            return x * 2
            
        # Patch get_tracer in tool_wrapper
        with patch('oao.runtime.tool_wrapper.get_tracer') as mock_get_tracer:
            mock_get_tracer.return_value = self.tracer
            
            wrapped = wrap_tool("my_tool", my_tool, context, None)
            wrapped(5)
            
            spans = self.exporter.get_finished_spans()
            self.assertEqual(len(spans), 1)
            self.assertEqual(spans[0].name, "oao.tool.my_tool")
            self.assertEqual(spans[0].attributes["tool.name"], "my_tool")

    def test_orchestrator_lifecycle_spans(self):
        # Mock dependencies
        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"
        
        # Patch dependencies
        with patch('oao.runtime.persistence.RedisPersistenceAdapter'), \
             patch('oao.runtime.orchestrator.get_tracer') as mock_get_tracer, \
             patch('oao.runtime.orchestrator.AdapterRegistry') as MockRegistry:
             
            mock_get_tracer.return_value = self.tracer
            
            mock_adapter = MagicMock()
            mock_adapter.plan.return_value = ["step1"]
            mock_adapter.execute.return_value = "result"
            mock_adapter.get_token_usage.return_value = 10
            MockRegistry.get_adapter.return_value = MagicMock(return_value=mock_adapter)
            
            # Use AsyncMock for execute_with_retry_async if needed, or stick to sync run
            orch = Orchestrator()
            
            # Run sync
            orch.run(mock_agent, "test task")
            
            # Verify get_tracer called
            self.assertTrue(mock_get_tracer.called)
            
            spans = self.exporter.get_finished_spans()
            span_names = [s.name for s in spans]
            
            self.assertIn("orchestrator.run_sync", span_names)
            self.assertIn("orchestrator.plan", span_names)
            self.assertIn("orchestrator.execute", span_names)
            self.assertIn("orchestrator.review", span_names)
            
            # Verify attributes on root span
            root_span = next(s for s in spans if s.name == "orchestrator.run_sync")
            self.assertEqual(root_span.attributes["agent.type"], "TestAgent")
