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
from oao.runtime.events import EventType

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
        
    def invoke(self, task):
        return {"output": "telemetry_success", "tokens": 10}

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
        
        async def run_workflow():
            orch = Orchestrator()
            agent = MockAgent()
            
            # This should generate spans
            report = await orch.run_async(agent, "test_telemetry_task")
            return report

        report = asyncio.run(run_workflow())
        
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
        
        print("✅ Telemetry verification successful")

if __name__ == "__main__":
    unittest.main()
