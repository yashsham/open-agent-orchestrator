"""
Prometheus metrics definition for OAO.
"""

try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    
    # Dummy classes for when prometheus_client is not installed
    class DummyMetric:
        def inc(self, amount=1): pass
        def dec(self, amount=1): pass
        def set(self, value): pass
        def observe(self, value): pass
        def time(self): return self
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def labels(self, *args, **kwargs): return self

    Counter = Histogram = Gauge = lambda *args, **kwargs: DummyMetric()


# ============================================================================
# Metrics Definitions
# ============================================================================

# Counters
execution_counter = Counter(
    "oao_executions_total",
    "Total number of orchestrations",
    ["status", "agent_type"]
)

token_usage_counter = Counter(
    "oao_token_usage_total",
    "Total tokens consumed by agents",
    ["agent_type"]
)

failures_counter = Counter(
    "oao_failures_total",
    "Total number of orchestration failures",
    ["error_type"]
)

# Histograms
execution_duration = Histogram(
    "oao_execution_duration_seconds",
    "Time taken for orchestration runs",
    ["agent_type"]
)

# Gauges
active_agents = Gauge(
    "oao_active_agents",
    "Number of currently running orchestrations"
)

queue_size = Gauge(
    "oao_queue_size",
    "Current size of distributed task queue"
)
