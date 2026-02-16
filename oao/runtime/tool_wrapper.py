from typing import Callable
from oao.telemetry import get_tracer

def wrap_tool(tool_name: str, tool_func: Callable, context: dict, policy):
    """
    Wrap a tool function to enforce OAO governance.
    """

    def wrapped(*args, **kwargs):
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span(f"oao.tool.{tool_name}") as span:
            span.set_attribute("tool.name", tool_name)
            
            # Increment tool call count
            context["tool_calls"] += 1

            # Policy validation before execution
            if policy:
                policy.validate(context)

            print(f"[TOOL CALL] {tool_name}")

            try:
                result = tool_func(*args, **kwargs)
                return result
            except Exception as e:
                span.record_exception(e)
                raise e

    return wrapped
