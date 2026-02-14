from oao.runtime.events import EventType


def console_logger(event):
    if event.event_type == EventType.STATE_ENTER:
        print(f"[EVENT] Entered state: {event.payload['state']}")

    elif event.event_type == EventType.TOOL_CALL:
        print(f"[EVENT] Tool call detected")

    elif event.event_type == EventType.POLICY_VIOLATION:
        print(f"[EVENT] Policy violation: {event.payload['error']}")

    elif event.event_type == EventType.EXECUTION_COMPLETE:
        print("[EVENT] Execution completed")
