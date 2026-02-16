from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
import os

_TRACER_INITIALIZED = False

def init_telemetry(service_name: str = "open-agent-orchestrator"):
    """
    Initialize OpenTelemetry Tracing.
    In a real system, you would configure OTLP exporter here.
    For now, we use a ConsoleExporter or NoOp if dependencies missing.
    """
    global _TRACER_INITIALIZED
    if _TRACER_INITIALIZED:
        return

    provider = TracerProvider()
    
    # Check for OTLP configuration
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
            print(f"[TELEMETRY] OTLP Exporter configured for {service_name} at {otlp_endpoint}")
        except ImportError:
            print("[TELEMETRY] OTLP Exporter not found. Install opentelemetry-exporter-otlp. Falling back to Console.")
            processor = SimpleSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
    else:
        # Export traces to console for visibility in demos
        processor = SimpleSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        print(f"[TELEMETRY] Console Exporter configured (OTEL_EXPORTER_OTLP_ENDPOINT not set)")

    trace.set_tracer_provider(provider)
    _TRACER_INITIALIZED = True
    print(f"[TELEMETRY] Initialized OpenTelemetry for {service_name}")

def get_tracer(name: str):
    return trace.get_tracer(name)
