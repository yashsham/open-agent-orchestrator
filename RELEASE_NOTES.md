# OpenAgentOrchestrator v1.0.0

**Production Ready Release** - The "Enterprise Hardened" control plane for AI agents.

This release marks a major milestone, introducing a complete suite of features for running mission-critical agent workloads.

## 🌟 Key Features

### 🛡️ Fault Tolerance & Reliability
- **Crash Recovery**: The Distributed Scheduler now automatically detects dead workers and re-queues their jobs.
- **Worker Heartbeats**: Active health monitoring for all worker nodes.
- **Atomic Job Claiming**: Zero data loss during job assignment using `RPOPLPUSH`.
- **Durable DAGs**: Workflow state is persisted to Redis, allowing resumption after failures.

### 🕸️ DAG Orchestration
- **Complex Workflows**: Define dependencies between agents using `TaskGraph`.
- **Parallel Execution**: Independent tasks run concurrently.
- **State Recovery**: Skip already completed tasks when resuming a workflow.

### 📊 Observability
- **Prometheus Integration**: Native `/metrics` endpoint.
- **Key Metrics**:
  - `oao_executions_total`
  - `oao_active_agents`
  - `oao_job_requeued_total` (New!)
  - `oao_token_usage_total`
- **Deep Metrics (OpenTelemetry)**:
  - Distributed tracing for full workflow visualization.
  - Trace context propagation across async tasks and DAG nodes.
  - Spans for `Orchestrator.run`, `Agent.step`, and `Tool.execute`.

### 🔌 Enterprise Plugin System
- **Extensible Architecture**: Load custom Policies, Schedulers, and Event Listeners dynamically.
- **Secure Plugins**: New `PluginInterface` enforces structure and version compatibility.
- **Plugin Loader**: Simply point to a Python module to extend OAO.

### ⚡ Distributed Scheduler
- **Redis-Backed**: Horizontally scale workers across multiple nodes.
- **Robust Queueing**: Handles network blips and transient failures with retry logic.

## Upgrading
Upgrade from PyPI:
```bash
pip install --upgrade open-agent-orchestrator
```

## Contributors
Thanks to the core team for getting us to v1.0.0!

---

# OpenAgentOrchestrator v0.1.1
*Packaging Fix Release*
- Fixed `uv.lock` packaging issue.
- Removed unused modules.
