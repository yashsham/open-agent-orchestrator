# 🚀 OAO Production Deployment Guide

This guide details how to deploy Open Agent Orchestrator (OAO) in a production environment with full persistence, recovery, and observability.

---

## 1. Infrastructure Requirements

### Redis (Mandatory for Persistence)
OAO uses Redis as its source of truth for:
-   **Persistence**: Workflow and agent state snapshots.
-   **Event Store**: Immutable event-sourced audit logs.
-   **Job Queue**: (If using distributed workers).

**Recommended Configuration:**
-   Redis 6.2+
-   `appendonly yes` (for durability)
-   `volatile-lru` evasion policy (OAO sets expiries on logs)

---

## 2. Environment Configuration

Set the following environment variables in your deployment environment:

```bash
# Redis Connection
REDIS_URL=redis://user:password@hostname:6379/0

# Observability (OpenTelemetry)
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_SERVICE_NAME=oao-runtime
OTEL_RESOURCE_ATTRIBUTES=env=production,version=1.1.0

# Logging
OAO_LOG_LEVEL=INFO
```

---

## 3. Deployment Topology

### A. Monolithic Deployment
Run the orchestrator and agent logic within the same process. Ideal for single-node applications.

```python
from oao.runtime.orchestrator import Orchestrator
from oao.runtime.persistence import RedisPersistenceAdapter
from oao.runtime.event_store import RedisEventStore

# Production setup
orchestrator = Orchestrator(
    persistence=RedisPersistenceAdapter(redis_url=os.getenv("REDIS_URL")),
    event_store=RedisEventStore(redis_url=os.getenv("REDIS_URL"))
)
```

### B. Distributed Workers (Experimental)
Separation of the OAO Brain and GPU-bound Muscles.

1.  **API Node:** Handles execution requests and status polling.
2.  **Worker Node:** Pulls jobs from Redis, executes the orchestrator loop.

---

## 4. Observability Setup

OAO emits traces to any OTLP-compatible backend (Jaeger, Honeycomb, Tempo).

1.  **Jaeger Setup (Local/Staging):**
    ```bash
    docker run -d --name jaeger \
      -e COLLECTOR_OTLP_ENABLED=true \
      -p 4317:4317 \
      -p 16686:16686 \
      jaegertracing/all-in-one:latest
    ```
2.  **Visualization:**
    -   Access `http://localhost:16686` to see the **Execution Timeline**.
    -   OAO spans are named `oao.step.N` and `oao.tool.name`.

---

## 5. Maintenance & Retention

### Event Log Clean-up
OAO sets a **7-day retention** on Redis event logs by default. You can adjust this in `RedisEventStore`:

```python
# To change retention (in seconds)
event_store.append_event(execution_id, event, expire=86400) # 24 hours
```

### Recovery Auditing
Monitor for `RETRY_ATTEMPTED` events in your logs. Frequent retries may indicate unstable external tools or networking issues.
