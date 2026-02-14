# OpenAgentOrchestrator v0.1.1

**Packaging fix release** - Resolved critical packaging issues from v0.1.0.

## Fixes
- **Removed `uv.lock`**: Lock files should not be included in PyPI distributions
- **Removed unused `api_models.py`**: Cleaned up unused module for better code quality
- **Added FastAPI import guards**: Protected optional server dependencies with proper error messages
- **Fixed orchestrator adapter error handling**: Improved error messages when adapters fail to load

## Features (from v0.1.0)
- **Deterministic lifecycle engine**: Strict execution flow (INIT → PLAN → EXECUTE → REVIEW → TERMINATE)
- **Strict policy enforcement**: Built-in limits for steps, tokens, and tool calls
- **Adapter registry**: Pluggable architecture supports LangChain (and future frameworks)
- **Async execution engine**: High-throughput `run_async` support
- **Multi-agent orchestration**: Run multiple agents concurrently under centralized governance
- **Parallel scheduler**: Controlled concurrency with error isolation
- **FastAPI server wrapper**: Production-ready API endpoints (`/run`, `/run-multi`)

## Installation
```bash
pip install open-agent-orchestrator
```

For server and LangChain support:
```bash
pip install "open-agent-orchestrator[server,langchain]"
```
