# 🏗️ OAO Architecture

This document details the internal architecture of the Open Agent Orchestrator (OAO), focusing on its deterministic execution model and event-sourced core.

---

## 1. Structural Overview

OAO is built on a modular, adapter-based architecture that decouples agent logic from execution concerns.

```mermaid
graph TD
    Client[Client Application] -->|Task| ORCH[Orchestrator]
    
    subgraph "Core Runtime"
        ORCH --> SM[State Machine]
        ORCH --> EB[Event Bus]
        ORCH --> TELEM[OpenTelemetry]
    end
    
    subgraph "Persistence Layer"
        ORCH --> ES[Event Store]
        ORCH --> PERS[Persistence Adapter]
        ES -->|Redis/In-Memory| ES_STORE[(Sorted Sets)]
        PERS -->|Redis/In-Memory| PERS_STORE[(Key-Value)]
    end
    
    subgraph "Execution Layer"
        ORCH --> ADAPT[Framework Adapter]
        ADAPT --> AGENT[AI Agent]
        ADAPT --> TW[Tool Wrapper]
        TW -->|Idempotency| ES
    end
    
    ORCH --> POL[Governance Policy]
```

---

## 2. Event-Sourced Lifecycle

Every execution follows a strict state-machine driven lifecycle where transitions are recorded as immutable events.

```mermaid
sequenceDiagram
    participant C as Client
    participant O as Orchestrator
    participant ES as Event Store
    participant AD as Adapter
    participant P as Policy

    C->>O: run(agent, task)
    O->>ES: append(EXECUTION_STARTED)
    
    loop until TERMINAL
        O->>P: validate(context)
        O->>ES: append(STATE_ENTER: EXECUTE)
        O->>AD: execute(task)
        AD->>O: result
        O->>ES: append(STEP_COMPLETED)
    end
    
    O->>ES: append(EXECUTION_COMPLETED)
    O->>C: ExecutionReport
```

---

## 3. Crash Recovery Flow

OAO guarantees state reconstruction and at-least-once execution via its recovery protocol.

```mermaid
graph TD
    CRASH[Worker Crash] --> DETECT[Recovery Manager Detects Failure]
    DETECT --> LOAD[Load Event Log from Event Store]
    LOAD --> REPLAY[Replay Events to State Machine]
    REPLAY --> SYNC[Restore Step Count & Tokens]
    SYNC --> RESUME[Resume from First Incomplete Step]
    RESUME --> IDEM[Idempotency Check for Tools]
```

---

## 4. Tool Idempotency Logic

To prevent duplicate side-effects during retries or recovery, OAO hashes tool calls.

```mermaid
flowchart LR
    CALL[Tool Call] --> HASH[Compute Args Hash]
    HASH --> CHECK{Hash in EventLog?}
    CHECK -->|Yes| SKIP[Return Previous Result]
    CHECK -->|No| EXEC[Execute Tool]
    EXEC --> PERSIST[Record Result + Hash in EventStore]
    PERSIST --> RET[Return Fresh Result]
```
