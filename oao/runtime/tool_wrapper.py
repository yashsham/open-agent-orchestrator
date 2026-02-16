import hashlib
import json
from typing import Callable, Any
from oao.telemetry import get_tracer
from oao.runtime.events import Event, EventType, ExecutionEvent

def compute_tool_hash(tool_name: str, args: tuple, kwargs: dict) -> str:
    """Compute a unique hash for a tool call."""
    canonical = {
        "name": tool_name,
        "args": args,
        "kwargs": kwargs
    }
    # Sort keys for deterministic hashing
    payload = json.dumps(canonical, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()

def wrap_tool(tool_name: str, tool_func: Callable, context: dict, policy):
    """
    Wrap a tool function to enforce OAO governance and ensure idempotency.
    """

    def wrapped(*args, **kwargs):
        tracer = get_tracer(__name__)
        execution_id = context.get("execution_id")
        event_store = context.get("event_store")
        
        with tracer.start_as_current_span(f"oao.tool.{tool_name}") as span:
            span.set_attribute("tool.name", tool_name)
            
            # Idempotency check
            tool_hash = None
            if execution_id and event_store:
                tool_hash = compute_tool_hash(tool_name, args, kwargs)
                # Check for existing result in event log
                events = event_store.get_events(execution_id)
                for e in events:
                    if e.event_type == EventType.TOOL_CALL_SUCCESS:
                        if e.input_data and e.input_data.get("tool_hash") == tool_hash:
                            print(f"[IDEMPOTENCY] Skipping duplicate call to {tool_name} (hash matches)")
                            span.set_attribute("idempotent.skipped", True)
                            return e.output_data.get("result") if e.output_data else None

            # Increment tool call count
            context["tool_calls"] += 1

            # Policy validation before execution
            if policy:
                policy.validate(context)

            print(f"[TOOL CALL] {tool_name}")

            try:
                result = tool_func(*args, **kwargs)
                
                # Persist completion event for idempotency
                if execution_id and event_store and tool_hash:
                    # We use a simplified event for tool completion records
                    # Note: Full ExecutionEvent requires more context (step_number etc)
                    # For now we use the context's current step
                    completion_event = ExecutionEvent(
                        execution_id=execution_id,
                        step_number=context.get("step_count", 0),
                        event_type=EventType.TOOL_CALL_SUCCESS,
                        input_data={"tool_name": tool_name, "tool_hash": tool_hash},
                        output_data={"result": result}
                    )
                    event_store.append_event(execution_id, completion_event)

                return result
            except Exception as e:
                span.record_exception(e)
                raise e

    return wrapped
