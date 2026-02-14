from typing import Callable


def wrap_tool(tool_name: str, tool_func: Callable, context: dict, policy):
    """
    Wrap a tool function to enforce OAO governance.
    """

    def wrapped(*args, **kwargs):

        # Increment tool call count
        context["tool_calls"] += 1

        # Policy validation before execution
        if policy:
            policy.validate(context)

        print(f"[TOOL CALL] {tool_name}")

        result = tool_func(*args, **kwargs)

        return result

    return wrapped
