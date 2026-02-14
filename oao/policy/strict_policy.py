import time


class PolicyViolation(Exception):
    pass


class StrictPolicy:
    """
    Enforces strict governance rules for agent execution.
    """

    def __init__(
        self,
        max_tokens: int = 4000,
        max_steps: int = 10,
        max_tool_calls: int = 5,
        timeout_seconds: int = 30,
    ):
        self.max_tokens = max_tokens
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        self.timeout_seconds = timeout_seconds

        self.start_time = None

    def start_timer(self):
        self.start_time = time.time()

    def validate(self, context: dict):
        """
        Validate execution constraints.
        """

        # Timeout check
        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed > self.timeout_seconds:
                raise PolicyViolation("Execution timeout exceeded")

        # Step limit check
        steps = context.get("step_count", 0)
        if steps > self.max_steps:
            raise PolicyViolation("Maximum execution steps exceeded")

        # Token check (placeholder for now)
        tokens = context.get("token_usage", 0)
        if tokens > self.max_tokens:
            raise PolicyViolation("Maximum token limit exceeded")

        # Tool calls check (placeholder)
        tool_calls = context.get("tool_calls", 0)
        if tool_calls > self.max_tool_calls:
            raise PolicyViolation("Maximum tool calls exceeded")

