from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter

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
    # Export traces to console for visibility in demos
    processor = SimpleSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    _TRACER_INITIALIZED = True
    print(f"[TELEMETRY] Initialized OpenTelemetry for {service_name}")

def get_tracer(name: str):
    return trace.get_tracer(name)
