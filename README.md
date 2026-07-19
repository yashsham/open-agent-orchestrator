# 🔥 OpenAgentOrchestrator (OAO)

> The Control Plane for AI Agents.

OpenAgentOrchestrator (OAO) is a **Deterministic AI Execution Runtime (DAER)** designed to bring infrastructure-grade **governance**, **resilience**, and **observability** to AI agents.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)
![Enterprise Hardened](https://img.shields.io/badge/Enterprise-Hardened-blueviolet.svg)

While most agent frameworks focus on building agents, OAO focuses on **controlling them**.

OAO acts as a **control plane** on top of existing AI frameworks, enabling safe, measurable, and scalable execution of AI agents.

---

# 📚 Technical Resources via OAO

We are building a library of technical content to help you engineer reliable agents.

### 📝 Technical Blogs
- [**Deterministic AI Execution**](blog/deterministic-ai-execution.md): Why current agents fail in production and how to fix them.
- [**Why Agent Systems Need Governance**](blog/agent-governance.md): Implementing budgets, RBAC, and oversight.
- [**Replayable LLM Pipelines**](blog/replayable-pipelines.md): Time-travel debugging for AI workflows.

### 🎮 Demos
- [**Failure Prevention**](demos/failure_prevention.py): See `StrictPolicy` stopping runaway agents.
- [**Deterministic Replay**](demos/deterministic_replay.py): Resume crashed executions with zero state loss.

---

# 🛡️ Fault Tolerance & Persistence

## 💓 Robust Distributed Scheduler
- **Crash Recovery**: Automatically detects dead workers and re-queues their jobs.
- **Heartbeats**: Workers report liveness to prevent silent failures.
- **Safe Claiming**: Uses `RPOPLPUSH` to ensure zero job loss during assignment.
- **Retries**: Configurable exponential backoff for transient failures.

## 💾 Durable Event Sourcing
- **State Reconstruction**: Derives runtime state from immutable event logs for exactly-once correctness.
- **Side-Effect Idempotency**: Automated SHA-256 tool-call hashing prevents duplicate external actions during retries.
- **Resume-on-Failure**: Crashed workflows resume at the first incomplete step; completed work is skipped.
- **Auditable History**: Full execution trace stored in persistent storage (Redis or In-Memory).
- **Time-Travel Debugging**: Fork and replay past executions to reproduce bugs.

---

# 🚀 Why OAO?

Modern AI agent frameworks lack:

- ❌ Deterministic lifecycle control  
- ❌ Strict policy enforcement  
- ❌ Tool-level governance  
- ❌ Execution observability  
- ❌ Parallel scheduling control  
- ❌ Infrastructure-grade architecture  

OAO solves this.

---

# 🧠 Core Philosophy

OAO separates:

```
Agent Intelligence  ≠  Agent Governance
```

Frameworks build intelligence.  
OAO governs execution.

Think of OAO as:

> Kubernetes for AI Agents.

---

# ✨ Features

## 🧭 Deterministic Lifecycle Engine

Strict execution flow:

```
INIT → PLAN → EXECUTE → REVIEW → TERMINATE
```

No uncontrolled recursion.  
No hidden state transitions.

---

## 🔐 Policy Enforcement

Built-in `StrictPolicy` enforces:

- Maximum execution steps  
- Maximum token usage  
- Maximum tool calls  
- Maximum tool calls  
- Execution timeouts  

Violations trigger `PolicyViolation` events and halt execution.

Agents cannot bypass governance rules.

---

## 🔌 Adapter Architecture

Pluggable adapter system allows integration with external frameworks.

Currently supported:

- **LangChain Adapter**: With deep callback integration.
- **LangGraph Adapter**: Execute stateful graphs with managed telemetry.
- **CrewAI Adapter**: Kick off Crews or run individual Agents natively.
- **AutoGen Adapter**: Wrap conversation/initiations between ConversableAgents.
- **Agno AI Adapter**: Run Agno/Phidata agents with metric tracking.
- **LlamaIndex Adapter**: Wrap query engines and LlamaIndex agents.

Future roadmap:

- Enterprise custom adapters  

Adapters are fully decoupled from orchestration core.

---

## 🔄 Async Execution Engine

Supports both:

- Synchronous execution (`run`)
- Asynchronous execution (`run_async`)

Ready for scalable, high-throughput workloads.

---

## 👥 Multi-Agent Orchestration

Run multiple agents under centralized governance:

- Independent lifecycle control  
- Independent execution reports  
- Controlled scheduling layer  

---

## 🖥️ Observability Dashboard

Real-time visibility into the Deterministic AI Execution Runtime (DAER):

- **Live Event Bridge**: Stream execution events via WebSockets (`/ws/events`).
- **Trace Timeline**: Gantt-chart visualization of tool calls and step durations.
- **Governance Watch**: Real-time tracking of token consumption and budget violations.
- **Scenario Simulation**: Internal hooks for testing and fine-tuning agent behavior.

---

## ⚡ Parallel Agent Scheduler

Built-in concurrency management:

- Configurable max concurrency  
- Async worker pool  
- Safe task isolation  
- Error containment  

---

## 🌐 FastAPI Server (OAO as Service)

Expose OAO as an HTTP backend:

- Single-agent endpoint  
- Multi-agent endpoint  
- Swagger documentation  
- Production-ready API layer  

---

## 📊 Structured Execution Reports

Every execution generates:

- Unique execution ID  
- Agent name  
- Status (SUCCESS / FAILED)  
- Total steps  
- Token usage  
- Tool usage  
- Execution time  
- State history  
- Final output  

Designed for observability and monitoring.

---

## 🎛 Event Hook System

OAO emits structured lifecycle events:

- STATE_ENTER  
- TOOL_CALL  
- POLICY_VIOLATION  
- EXECUTION_COMPLETE  

Hooks enable:

- Logging  
- Metrics  
- Monitoring  
- External integrations  

---

# 📦 Installation

Install from PyPI:

```bash
pip install open-agent-orchestrator
```

> [!NOTE]
> By default, `Orchestrator` runs locally in memory out-of-the-box with **zero Redis connection or package dependencies required**.

### Optional Dependencies

Install only the adapters you need to keep dependencies lightweight:

```bash
# Install with API server and specific framework support
pip install "open-agent-orchestrator[server,langchain,langgraph,crewai,autogen,agno,llamaindex]"
```

Or install locally:

```bash
pip install -e ".[all]"
```

---

# ⚡ Quick Start (Single Agent)

```python
from oao import Orchestrator, StrictPolicy

class DummyAgent:
    def invoke(self, task):
        return {"output": f"Processed: {task}"}

policy = StrictPolicy(max_steps=5)

orch = Orchestrator(policy=policy)

report = orch.run(
    agent=DummyAgent(),
    task="Explain AI orchestration",
)

print(report.model_dump_json(indent=2))
```

---

# ⚡ Async Execution

```python
import asyncio
from oao import Orchestrator

class DummyAgent:
    def invoke(self, task):
        return {"output": f"Processed: {task}"}

async def main():
    orch = Orchestrator()
    report = await orch.run_async(
        agent=DummyAgent(),
        task="Async execution demo"
    )
    print(report.model_dump_json(indent=2))

asyncio.run(main())
```

---

# 👥 Multi-Agent Example

```python
import asyncio
from oao.runtime.multi_agent import MultiAgentOrchestrator

class DummyAgent:
    def __init__(self, name):
        self.name = name

    def invoke(self, task):
        return {"output": f"{self.name} processed: {task}"}

agents = {
    "researcher": DummyAgent("Researcher"),
    "critic": DummyAgent("Critic"),
}

async def main():
    multi = MultiAgentOrchestrator(max_concurrency=2)

    results = await multi.run_multi_async(
        agents=agents,
        task="Discuss AI governance"
    )

    for name, report in results.items():
        print(name, report.status)

asyncio.run(main())
```

---

# 🕸️ DAG Orchestration

Execute complex workflows with dependencies and automatic parallelism.

```python
from oao.runtime.dag import TaskGraph, GraphExecutor, TaskNode

# Define graph
graph = TaskGraph()
graph.add_node(TaskNode("research", agent_researcher, "Research topic X"))
graph.add_node(TaskNode("draft", agent_writer, "Draft article", dependencies={"research"}))
graph.add_node(TaskNode("critique", agent_critic, "Critique draft", dependencies={"research"}))
graph.add_node(TaskNode("polisher", agent_polisher, "Improve draft", dependencies={"critique", "draft"}))

# Execute
executor = GraphExecutor(graph)
results = executor.execute("Write a blog post about AI")
```

Features:
- **Topological Sorting**: Ensures corect execution order.
- **Cycle Detection**: Prevents infinite loops.
- **Parallel Execution**: Independent branches run concurrently.
- **Context Passing**: Results flow from dependencies to dependents.

---

# 🌐 Run as API Service

Start server:

```bash
# Ensure server dependencies are installed
pip install "open-agent-orchestrator[server]"

uvicorn oao.server:app --reload
```

Open:

```
http://127.0.0.1:8000/docs
```

Available endpoints:

- `POST /run`
- `POST /run-multi`

---

# 📊 Observability (Metrics & Tracing)

OAO provides deep visibility into your agent fleets.

### Prometheus Metrics
Exposed at `/metrics`:
- `oao_executions_total`: Execution counter (status, agent_type)
- `oao_execution_duration_seconds`: Histogram of execution time
- `oao_active_agents`: Gauge of concurrent agents
- `oao_token_usage_total`: Token consumption counter
- `oao_queue_size`: Distributed queue depth

### OpenTelemetry Tracing
Full distributed tracing for workflows. Configure via `OTEL_EXPORTER_OTLP_ENDPOINT`.

- **Root Spans**: `orchestrator.run`, `dag.execute`
- **Child Spans**: `oao.step.N`, `tool.execute`, `dag.schedule_task`
- **Context Propagation**: Trace IDs flow across async tasks and Redis queues.

---

# 🔌 Enterprise Plugin System

Extend OAO without modifying core code. Built on a **Secure Plugin Interface**.

### 1. Create a Plugin (`my_plugin.py`)

Plugins must implement `PluginInterface`:

```python
from oao.plugins.base import PluginInterface
from oao.policy.registry import PolicyRegistry

class MyPlugin(PluginInterface):
    @property
    def name(self): return "my_security_plugin"
    
    @property
    def version(self): return "1.0.0"

    def activate(self):
        # Register custom components safely
        PolicyRegistry.register("custom_policy", MyCustomPolicy)
        
    def deactivate(self):
        pass
```

### 2. Load the Plugin

```python
from oao.plugins.loader import PluginLoader

# Verifies signature and version before loading
PluginLoader.load("path/to/my_plugin.py")
```

Supports custom:
- Policies (Governance)
- Schedulers (Execution strategy)
- Event Listeners (Logging/Tracing)
- Adapters (Framework support)

---

# 🏗 Architecture Overview

```
Client / CLI / Dashboard
            ↓
        FastAPI Server
            ↓
     OAO Orchestrator Core
            ↓
   Adapter → External Framework
```

- Lifecycle State Machine  
- Policy Engine (Stop-Loss Governance)
- Adapter Registry (LangChain, LangGraph)
- **Hash-Based Tool Interception Layer**
- **Append-Only Event Bus**
- Execution Report Generator  
- Parallel Scheduler  
- Multi-Agent Coordinator  

See the [Detailed Architecture Guide](docs/architecture.md) for Mermaid diagrams and recovery flows.

---

# 🔒 Governance Model

OAO enforces:

- Deterministic state transitions  
- Token budgeting  
- Tool access limits  
- Execution boundaries  
- Timeout enforcement  

Agents cannot override governance rules.

---

# 🧪 Project Structure

```
oao/
 ├── runtime/
 ├── adapters/
 ├── policy/
 ├── protocol/
 ├── server.py
 ├── cli.py
```

---

# 📈 Roadmap

- [x] Deterministic lifecycle engine  
- [x] Strict policy enforcement  
- [x] Adapter abstraction  
- [x] Async execution engine  
- [x] Multi-agent orchestration  
- [x] Parallel scheduler  
- [x] FastAPI service  
- [x] Web dashboard  
- [x] Distributed scheduler (Redis)  
- [x] DAG-based orchestration  
- [x] Metrics exporter  
- [x] Enterprise plugin ecosystem  
- [x] Crash Recovery & Replay
- [x] Tool Idempotency Wrapper
- [x] Event-Sourced Determinism (DAER)
- [x] OpenTelemetry Tracing  
- [x] LangGraph Support
- [x] CrewAI Support
- [x] AutoGen Support
- [x] Agno AI (Phidata) Support
- [x] LlamaIndex Support

---

# 🤝 Contributing

Contributions are welcome.

Guidelines:

- Maintain clean architecture principles  
- Keep lifecycle deterministic  
- Preserve adapter abstraction  
- Add tests for new modules  

---

# 📜 License

MIT License

---

# 🧠 Vision

OAO aims to become:

> The Infrastructure Layer for AI Agents.

As AI agents become more autonomous, governance becomes essential.

OAO ensures agents remain:

- **Observable**  
- **Measurable**  
- **Controllable**  
- **Scalable**  
- **Safe**  

---

# ⭐ Support

If you find OAO useful:

- Star the repository  
- Contribute adapters  
- Build plugins  
- Share with the AI community  

Let’s define the control plane for AI systems.
