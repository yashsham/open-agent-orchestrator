# 🔥 OpenAgentOrchestrator (OAO)

> The Control Plane for AI Agents.

OpenAgentOrchestrator (OAO) is an infrastructure-grade orchestration engine designed to bring **governance**, **determinism**, and **observability** to AI agents.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)

While most agent frameworks focus on building agents, OAO focuses on **controlling them**.

OAO acts as a **control plane** on top of existing AI frameworks, enabling safe, measurable, and scalable execution of AI agents.

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
- Execution timeouts  

Agents cannot bypass governance rules.

---

## 🔌 Adapter Architecture

Pluggable adapter system allows integration with external frameworks.

Currently supported:

- LangChain Adapter

Future roadmap:

- CrewAI  
- AutoGen  
- LlamaIndex  
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

### Optional Dependencies

For running the API server or using LangChain adapters:

```bash
# Install with API server and LangChain support
pip install "open-agent-orchestrator[server,langchain]"
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

print(report.json(indent=2))
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
    print(report.json(indent=2))

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

Core Components:

- Lifecycle State Machine  
- Policy Engine  
- Adapter Registry  
- Tool Interception Layer  
- Event Bus  
- Execution Report Generator  
- Parallel Scheduler  
- Multi-Agent Coordinator  

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
- [ ] Distributed scheduler (Redis)  
- [ ] DAG-based orchestration  
- [ ] Metrics exporter  
- [ ] Enterprise plugin ecosystem  

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

- Observable  
- Measurable  
- Controllable  
- Scalable  
- Safe  

---

# ⭐ Support

If you find OAO useful:

- Star the repository  
- Contribute adapters  
- Build plugins  
- Share with the AI community  

Let’s define the control plane for AI systems.
