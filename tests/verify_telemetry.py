import unittest
import asyncio
import sys
import os
import time
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Ensure oao is in py path
sys.path.insert(0, os.getcwd())

from oao.runtime.orchestrator import Orchestrator
from oao.runtime.events import EventType, ExecutionEvent

# Mock Agent
class MockAgent:
    name = "telemetry_test_agent"
    
    def plan(self, task):
        return {"action": "mock_action"}
        
    def execute(self, plan, context=None, policy=None):
        return {"output": "telemetry_success", "tokens": 10}
        
    async def execute_async(self, plan, context=None, policy=None):
        await asyncio.sleep(0.1)
        return {"output": "telemetry_success", "tokens": 10}
        
    async def invoke_async(self, task):
        return {"output": "telemetry_success", "tokens": 10}
        
    def invoke(self, input, **kwargs):
        print(f"[MOCK] Invoked with: {input}")
        return {"output": "Mock response"}

class TestTelemetry(unittest.TestCase):
    
    def setUp(self):
        # Setup In-Memory Exporter
        self.exporter = InMemorySpanExporter()
        provider = TracerProvider()
        processor = SimpleSpanProcessor(self.exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        
    def test_tracing_enabled(self):
        print("\nTesting OpenTelemetry Tracing...")
        
        from unittest.mock import MagicMock
        
        async def run_workflow():
            mock_persistence = MagicMock()
            orch = Orchestrator(persistence=mock_persistence)
            agent = MockAgent()
            
            # This should generate spans
            report = await orch.run_async(agent, "test_telemetry_task")
            return orch, report

        orch, report = asyncio.run(run_workflow())
        
        self.assertEqual(report.status, "SUCCESS")
        
        # Verify Spans
        spans = self.exporter.get_finished_spans()
        print(f"Captured {len(spans)} spans")
        
        span_names = [s.name for s in spans]
        print(f"Span names: {span_names}")
        
        # We expect at least 'orchestrator.run'
        self.assertIn("orchestrator.run", span_names)
        
        # Check attributes
        root_span = next(s for s in spans if s.name == "orchestrator.run")
        self.assertEqual(root_span.attributes.get("agent.type"), "telemetry_test_agent")
        self.assertEqual(root_span.status.status_code, trace.StatusCode.UNSET) # Success usually leaves it unset unless ERROR
        
        # Verify Step Spans
        step_spans = [s for s in spans if s.name.startswith("oao.step.")]
        print(f"Captured {len(step_spans)} step spans")
        self.assertTrue(len(step_spans) > 0, "No step spans captured")
        
        # Verify events have trace IDs
        events = orch.get_events(report.execution_id)
        print(f"Captured {len(events)} events")
        
        traced_events = [e for e in events if e.trace_id is not None]
        print(f"Events with trace_id: {len(traced_events)}")
        
        # At least STATE_ENTER events should have trace_id (created inside step loop)
        self.assertTrue(len(traced_events) > 0, "No events have trace_id")
        
        # Verify trace_id matches root span trace_id
        root_trace_id = format(root_span.context.trace_id, "032x")
        self.assertEqual(traced_events[0].trace_id, root_trace_id)
        
        print("[SUCCESS] Telemetry verification successful")

if __name__ == "__main__":
    unittest.main()
