from typing import Any

from oao.adapters.base_adapter import BaseAdapter
from oao.runtime.tool_wrapper import wrap_tool


class LangChainAdapter(BaseAdapter):
    """
    Adapter for LangChain-based agents or runnables.

    This adapter requires the optional dependency:
        pip install open-agent-orchestrator[langchain]
    """

    def __init__(self, agent: Any):
        self._ensure_langchain_installed()
        self.agent = agent
        self._token_usage = 0

    # =====================================================
    # Dependency Guard
    # =====================================================

    def _ensure_langchain_installed(self):
        try:
            import langchain  # noqa: F401
        except ImportError:
            raise ImportError(
                "LangChain is not installed.\n"
                "Install it with:\n"
                "    pip install open-agent-orchestrator[langchain]"
            )

    # =====================================================
    # Tool Wrapping
    # =====================================================

    def _wrap_tools(self, context: dict, policy):

        if hasattr(self.agent, "tools") and self.agent.tools:

            wrapped_tools = []

            for tool in self.agent.tools:

                wrapped_func = wrap_tool(
                    tool_name=getattr(tool, "name", "unknown_tool"),
                    tool_func=tool.func,
                    context=context,
                    policy=policy,
                )

                tool.func = wrapped_func
                wrapped_tools.append(tool)

            self.agent.tools = wrapped_tools

    # =====================================================
    # Lifecycle Methods
    # =====================================================

    def plan(self, task: str) -> str:
        """
        For MVP, plan simply returns the task.
        Advanced planning logic can be added later.
        """
        return task

    def execute(self, task: str, context: dict = None, policy=None) -> Any:
        """
        Synchronous execution.
        """

        if context is not None:
            self._wrap_tools(context, policy)

        result = self.agent.invoke(task)

        self._extract_token_usage(result)

        return result

    async def execute_async(self, task: str, context: dict = None, policy=None) -> Any:
        """
        Asynchronous execution.
        Runs blocking invoke() inside a thread pool.
        """

        import asyncio

        if context is not None:
            self._wrap_tools(context, policy)

        loop = asyncio.get_event_loop()

        result = await loop.run_in_executor(
            None,
            lambda: self.agent.invoke(task),
        )

        self._extract_token_usage(result)

        return result

    # =====================================================
    # Token Tracking
    # =====================================================

    def _extract_token_usage(self, result: Any):
        """
        Attempt to extract token usage if available.
        """

        try:
            if isinstance(result, dict) and "usage" in result:
                usage = result.get("usage", {})
                self._token_usage = usage.get("total_tokens", 0)
            else:
                self._token_usage = 0
        except Exception:
            self._token_usage = 0

    def get_token_usage(self) -> int:
        return self._token_usage


# =====================================================
# Adapter Registration
# =====================================================

from oao.adapters.registry import AdapterRegistry

AdapterRegistry.register("langchain", LangChainAdapter)
