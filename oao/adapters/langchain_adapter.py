from typing import Any, List
import asyncio

from oao.adapters.base_adapter import BaseAdapter
from oao.runtime.tool_wrapper import wrap_tool
from oao.adapters.registry import AdapterRegistry


class LangChainAdapter(BaseAdapter):
    """
    Adapter for LangChain-based agents or runnables.
    """

    def __init__(self, agent: Any):
        self.agent = agent
        self._token_usage = 0

    def _wrap_tools(self, context: dict, policy):

        # If agent has tools attribute
        if hasattr(self.agent, "tools"):

            wrapped_tools = []

            for tool in self.agent.tools:

                wrapped_func = wrap_tool(
                    tool_name=tool.name,
                    tool_func=tool.func,
                    context=context,
                    policy=policy,
                )

                tool.func = wrapped_func
                wrapped_tools.append(tool)

            self.agent.tools = wrapped_tools

    def plan(self, task: str) -> str:
        return task

    def execute(self, task: str, context: dict = None, policy=None) -> Any:

        # Wrap tools before execution
        if context is not None:
            self._wrap_tools(context, policy)

        result = self.agent.invoke(task)

        # Try to extract token usage if available
        try:
            usage = result.get("usage", {})
            self._token_usage = usage.get("total_tokens", 0)
        except Exception:
            self._token_usage = 0

        return result

    async def execute_async(self, task: str, context: dict = None, policy=None):

        if context is not None:
            self._wrap_tools(context, policy)

        # Run blocking invoke in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.agent.invoke(task)
        )

        try:
            usage = result.get("usage", {})
            self._token_usage = usage.get("total_tokens", 0)
        except Exception:
            self._token_usage = 0

        return result

    def get_token_usage(self) -> int:
        return self._token_usage

# Register this adapter
AdapterRegistry.register("langchain", LangChainAdapter)



