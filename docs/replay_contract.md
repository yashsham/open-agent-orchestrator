# 🔄 OAO Replay Contract

The Replay Contract defines how the OAO runtime reconstructs state and re-executes workflows from the event log.

---

## 1. Replay Definition

Replay is the process of loading an existing `EventLog` and re-submitting events to the `Orchestrator`'s state machine to reach a specific point in time or to resume execution.

---

## 2. Rehydration Protocol (The "Safe" Path)

The default replay mode is **Rehydration-only**.

-   **Process:**
    1.  Load all events from `EventStore`.
    2.  Instantiate a fresh `Orchestrator` with the original `ExecutionSnapshot`.
    3.  Sequentially apply events to the internal state machine.
    4.  **No Side Effects:** During rehydration, the adapter's `execute` method and tool calls are **skipped**.
-   **Guarantee:** The resulting `ExecutionState` is identical to the state at the time the last event was emitted.

---

## 3. Resumption Contract

When an execution is resumed (e.g., after a crash), it follows the **Skip-Completed** rule.

-   **Rule:** For every step index `N` already present in the `EventLog` as a `STEP_COMPLETED` event, the orchestrator MUST NOT trigger the agent logic or tool calls for that step.
-   **Boundary:** Resumption starts exactly at the first incomplete step index.
-   **Idempotency:** Because completed steps are skipped, duplicate side effects are prevented for all successfully finished work.

---

## 4. Forced Re-Execution (The "Audit" Path)

Forced re-execution allows re-running steps to verify determinism or debug logic.

-   **Policy:** By default, OAO restricts forced re-execution if it involves non-idempotent tool calls.
-   **Verification:** If re-execution produces a different sequence of events or a different state, the runtime must flag a **Determinism Violation**.

---

## 5. Trace & Hash Continuity

-   **Trace ID:** A replayed execution MUST maintain the same `trace_id` if it is a resumption of the same logical execution.
-   **Event Integrity:** Replay cannot append events to a log if the hash of the new state deviates from the historical record for existing steps.

---

## 6. Determinism Constraints

A successful replay depends on:
1.  **Immutable Code:** The agent logic and orchestrator version must ideally match the historical execution.
2.  **Stable Dependencies:** External tool definitions must be compatible.
3.  **Hashed Config:** The `ExecutionHash` must match.
