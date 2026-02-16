# 📜 OAO Execution Guarantees

This document formalizes the reliability, consistency, and durability guarantees provided by the Open Agent Orchestrator (OAO) runtime.

---

## 1. At-Least-Once Execution (Default)

OAO ensures that every task requested will be executed **at least once**.

-   **Mechanism:** Tasks are stored in a persistent queue (Redis). Workers must explicitly acknowledge task completion.
-   **Failure Scenario:** If a worker crashes mid-step, the `RecoveryManager` detects the heartbeat loss and re-queues the task.
-   **Impact:** Downstream agents or tools must be prepared for potential re-execution of the *current* step if a crash occurs at the boundary. However, OAO provides **Automatic Idempotency** as a layer of protection (see Section 6).

---

## 2. Deterministic State Reconstruction (Exactly-Once state)

While side effects (tool calls) follow *at-least-once* semantics without explicit idempotency guards, the **internal state** of the orchestrator is reconstructed with **exactly-once** correctness via event sourcing.

-   **Mechanism:** Every state transition is appended to an immutable `EventLog`.
-   **Recovery:** During recovery, the orchestrator "replays" events to reach the exact state before the crash.
-   **Guarantee:** The orchestrator will never transition to the same state twice for the same step index in a successful execution path.

---

## 3. Policy Hard-Stop Guarantee

OAO guarantees that governance policies (Max Steps, Max Tokens) are tested **before** every execution step.

-   **Mechanism:** The `Orchestrator` invokes `policy.validate()` at the start of the `while` loop.
-   **Consistency:** If a violation occurs, the system emits a `PolicyViolation` event and halts.
-   **Boundaries:** No tool calls or agent logic are executed once a policy limit is reached.

---

## 4. Immutable Execution Context

Once an execution is initialized, its core configuration and history are immutable.

-   **Mechanism:** `ExecutionSnapshot` is a frozen dataclass.
-   **Integrity:** Any attempt to resume or replay an execution with a modified configuration (different policy, different agent version) will result in an `ExecutionHashMismatch` error.
-   **Auditability:** The `execution_id` is cryptographically tied to the initial state.

---

## 5. Persistence Durability

-   **Standard:** OAO supports `RedisPersistenceAdapter` for production.
-   **Guarantee:** When using Redis, events are persisted before state transitions are considered successful.
    -   *Wait-for-Event:* The `EventStore` must confirm write before the orchestrator proceeds to the next step.
-   **Isolation:** Each execution ID lives in an isolated event namespace.

---

## 🎯 Summary Matrix

| Guarantee | Level | Mechanism |
| :--- | :--- | :--- |
| **Task Delivery** | At-Least-Once | Persistent Queue + Recovery Manager |
| **Internal State** | Exactly-Once | Event Sourcing + Replay |
| **Governance** | Hard-Stop | Pre-Execution Validation |
| **Data Integrity** | Immutable | Deterministic Hashing |
| **Durability** | Persistent | Write-Ahead Event Logging |
| **Idempotency** | Automated | Hash-based side-effect protection |

---

## 6. Tool Idempotency Guarantee

OAO provides a built-in idempotency layer to protect against unwanted side-effects during recovery or retries.

-   **Mechanism:** Every tool call is intercepted by a wrapper that computes a SHA-256 hash of the `(tool_name, args, kwargs)`.
-   **Verification:** Before execution, the runtime checks the `EventLog` for an existing `TOOL_CALL_SUCCESS` event with a matching hash.
-   **Guarantee:** If a duplicate tool call is detected within the same execution ID, the runtime skips execution and returns the historical result.
-   **Self-Healing:** This ensures that even "non-idempotent" external tools (e.g., sending an email) are safely wrapped by OAO to behave idempotently at the orchestration level.
