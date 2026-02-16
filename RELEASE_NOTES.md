# 🚀 OpenAgentOrchestrator v1.2.0

**Observability & Real-time Telemetry Update** - Introducing a high-performance dashboard and WebSocket event bridge for the DAER.

---

## 🌟 Key Features

### 🖥️ Observability Dashboard
- **WebSocket Bridge**: Real-time streaming of `EventBus` signals directly to the UI.
- **Trace Timeline**: Visual Gantt-chart representation of orchestration steps and tool-call spans.
- **Governance Widgets**: Real-time dashboards for token budgets and policy status.
- **React Dashboard**: A dedicated Vite + React frontend for infrastructure-grade monitoring.

### 🛡️ Runtime Formalization (DAER Hardening)
- **Direct Event Hooks**: Enhanced simulation and monitoring hooks for deep-dive testing.
- **Benchmark Hardening**: Verified sub-millisecond step overhead for complex agentic workflows.
- **Import Cleanup**: Standardized default logging and event dispatching.

---

# 🚀 OpenAgentOrchestrator v1.1.0

[![PyPI version](https://badge.fury.io/py/open-agent-orchestrator.svg)](https://pypi.org/project/open-agent-orchestrator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Deep Integration & Reliability Update** - Expanding the ecosystem with LangChain/LangGraph support and hardening distributed execution.

This release focuses on **interoperability** and **observability**. We've added persistent memory for LangChain, stateful graph execution for LangGraph, and full OpenTelemetry tracing for distributed workflows.

---

## 🌟 Key Features

### 🔌 Deep Integration
- **LangChain Support**: `LangChainAdapter` now includes:
    - **Persistent Memory**: `OAORedisChatMessageHistory` for durable conversation state.
    - **Event Bridging**: Maps internal LangChain events to OAO's governance layer.
- **LangGraph Support**: New `LangGraphAdapter` allows you to orchestrate complex state machines with OAO's policy enforcement and telemetry.

### 🛡️ Governance & Policy
- **Strict Hard-Stops**: Agents exceeding `max_steps` or `max_tokens` are now immediately terminated with a `PolicyViolation` event.
- **Granular Control**: Policy checks occur before every step execution to prevent runaway costs.

### 📊 Advanced Observability
- **OpenTelemetry Tracing**: Full OTLP support with dedicated spans for every execution step (`oao.step.N`).
- **Trace Context**: `trace_id` and `span_id` are now propagated in all `ExecutionEvent` payloads for distributed tracing.

### 🛡️ Formal Execution Hardening (DAER)
- **Event-Sourced Orchestrator**: The core runtime is now a Deterministic AI Execution Runtime (DAER). All state is derived from immutable event logs.
- **Side-Effect Idempotency**: Automated hash-based protection for tool calls prevents duplicate external actions during retries or recovery.
- **Dynamic Execution Hashing**: Hashes now include `oao.__version__` and adapter versions to ensure audit integrity across updates.
- **In-Memory Adapters**: New `InMemoryPersistenceAdapter` and `InMemoryEventStore` for high-speed testing and local benchmarking.

### ⚡ Performance Benchmarking
- **Low Overhead**: Measured runtime overhead of ~9ms per multi-step execution (~0.3ms per step after initialization).
- **Scalability**: Tested up to 100+ concurrent state transitions without performance degradation.

### 📚 Technical Content
- **New Blogs**: Deep dives into Deterministic Execution, Governance, and Replayability.
- **Architecture**: Comprehensive Mermaid diagrams for Lifecycle, Recovery, and Idempotency flows.

---

## 🐛 Bug Fixes
- Fixed race condition in Redis heartbeats during high concurrency.
- Resolved span context propagation issues in async tool calls.
- Improved error handling for missing optional dependencies (LangChain/LangGraph).

---

## 📦 Installation
```bash
pip install "open-agent-orchestrator[server,langchain,langgraph]"
```

---

# 🚀 OpenAgentOrchestrator v1.0.0

[![PyPI version](https://badge.fury.io/py/open-agent-orchestrator.svg)](https://pypi.org/project/open-agent-orchestrator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**Production Ready Release** - The "Enterprise Hardened" control plane for AI agents.

This release marks a major milestone, introducing a complete suite of features for running mission-critical agent workloads. OpenAgentOrchestrator (OAO) now delivers enterprise-grade orchestration with fault tolerance, distributed execution, and deep observability.

---

## 🌟 Key Features

### 🛡️ Fault Tolerance & Reliability
- **Crash Recovery**: The Distributed Scheduler now automatically detects dead workers and re-queues their jobs
- **Worker Heartbeats**: Active health monitoring for all worker nodes with configurable timeout thresholds
- **Atomic Job Claiming**: Zero data loss during job assignment using Redis `RPOPLPUSH` operations
- **Durable DAGs**: Workflow state is persisted to Redis, allowing seamless resumption after failures
- **Exponential Backoff**: Configurable retry logic for handling transient failures gracefully

### 🕸️ DAG Orchestration
- **Complex Workflows**: Define dependencies between agents using the intuitive `TaskGraph` API
- **Parallel Execution**: Independent tasks run concurrently, maximizing throughput
- **Topological Sorting**: Ensures correct execution order based on dependencies
- **Cycle Detection**: Prevents infinite loops in workflow definitions
- **State Recovery**: Automatically skip already completed tasks when resuming a workflow
- **Context Passing**: Results flow seamlessly from dependencies to dependent tasks

### 📊 Observability & Monitoring
- **Prometheus Integration**: Production-ready `/metrics` endpoint for monitoring
- **Key Metrics**:
  - `oao_executions_total` - Total execution counter with status labels
  - `oao_execution_duration_seconds` - Execution time histogram
  - `oao_active_agents` - Gauge of concurrent agent executions
  - `oao_job_requeued_total` - **NEW!** Track crash recovery and retries
  - `oao_token_usage_total` - Monitor LLM token consumption
  - `oao_queue_size` - Distributed queue depth tracking
- **OpenTelemetry Tracing**:
  - Distributed tracing for complete workflow visualization
  - Trace context propagation across async tasks and DAG nodes
  - Structured spans for `Orchestrator.run`, `Agent.step`, and `Tool.execute`
  - Export to Jaeger, Zipkin, or any OTLP-compatible backend

### 🔌 Enterprise Plugin System
- **Extensible Architecture**: Load custom Policies, Schedulers, and Event Listeners dynamically
- **Secure Plugin Interface**: New `PluginInterface` enforces structure and version compatibility
- **Plugin Loader**: Simply point to a Python module to extend OAO without modifying core code
- **Safe Activation**: Plugins execute in controlled environments with proper lifecycle management
- **Supports Custom**:
  - Policies (Governance and Compliance)
  - Schedulers (Execution Strategies)
  - Event Listeners (Logging/Tracing/Auditing)
  - Adapters (Framework Integration)

### ⚡ Distributed Scheduler
- **Redis-Backed**: Horizontally scale workers across multiple nodes and data centers
- **Robust Queueing**: Handles network blips and transient failures with automatic retry logic
- **Worker Pool Management**: Dynamic worker scaling based on queue depth
- **Job Priority Support**: Priority-based job scheduling for critical workloads
- **Dead Letter Queue**: Failed jobs are tracked and can be retried or analyzed

### 🚀 Additional Enhancements
- **Async-First Design**: Full async/await support for high-throughput workloads
- **Multi-Agent Coordination**: Run multiple agents under centralized governance
- **LangChain Adapter**: First-class integration with LangChain agents and tools
- **FastAPI Server**: Production-ready HTTP API with OpenAPI documentation
- **Structured Logging**: JSON-structured logs for easy parsing and analysis
- **Type Safety**: Comprehensive Pydantic models for all data structures

---

## 📦 Installation

### Fresh Install
```bash
pip install open-agent-orchestrator
```

### Upgrade from Previous Version
```bash
pip install --upgrade open-agent-orchestrator
```

### Install with Optional Dependencies
```bash
# For API server support
pip install "open-agent-orchestrator[server]"

# For LangChain integration
pip install "open-agent-orchestrator[langchain]"

# For distributed execution
pip install "open-agent-orchestrator[distributed]"

# Install everything
pip install "open-agent-orchestrator[all]"
```

---

## 🔗 Links

- **PyPI Package**: https://pypi.org/project/open-agent-orchestrator/1.0.0/
- **Documentation**: [README.md](https://github.com/yashsham/open-agent-orchestrator)
- **Issue Tracker**: [GitHub Issues](https://github.com/yashsham/open-agent-orchestrator/issues)

---

## 📝 Quick Start

```python
from oao import Orchestrator, StrictPolicy

class MyAgent:
    def invoke(self, task):
        return {"output": f"Processed: {task}"}

# Create orchestrator with governance policy
policy = StrictPolicy(max_steps=10, max_tokens=500000)
orch = Orchestrator(policy=policy)

# Run agent with full observability
report = orch.run(
    agent=MyAgent(),
    task="Analyze quarterly revenue trends"
)

print(f"Status: {report.status}")
print(f"Tokens Used: {report.token_usage}")
```

For more examples, see the [README.md](https://github.com/yashsham/open-agent-orchestrator).

---

## 🐛 Bug Fixes

- Fixed plugin loader version compatibility checks
- Resolved race condition in distributed scheduler heartbeat mechanism
- Corrected OpenTelemetry span context propagation in nested DAG executions
- Fixed memory leak in long-running multi-agent orchestrations

---

## ⚠️ Breaking Changes

None! This is a major version bump that maintains backward compatibility with v0.1.x.

---

## 🙏 Contributors

Thanks to the core team and community contributors for getting us to v1.0.0!

Special thanks to:
- [@yashsham](https://github.com/yashsham) - Core architecture and implementation

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

## 🎯 What's Next?

Looking ahead to v1.1.0:
- CrewAI and AutoGen adapters
- Built-in A/B testing framework for agent strategies
- Advanced cost optimization policies
- Web dashboard for real-time monitoring
- Kubernetes operator for cloud-native deployments

Stay tuned! ⭐

---

# OpenAgentOrchestrator v0.1.1
*Packaging Fix Release*
- Fixed `uv.lock` packaging issue.
- Removed unused modules.
