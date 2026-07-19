from typing import Any, Dict, Optional
import asyncio

from oao.adapters.base_adapter import BaseAdapter


class LlamaIndexAdapter(BaseAdapter):
    """
    Adapter for LlamaIndex-based agent runners/workers.
    """

    def __init__(self, agent: Any):
        self._ensure_llamaindex_installed()
        self.agent = agent
        self._token_usage = 0

    def _ensure_llamaindex_installed(self):
        try:
            import llama_index  # noqa: F401
        except ImportError:
            raise ImportError(
                "LlamaIndex is not installed.\n"
                "Install it with:\n"
                "    pip install open-agent-orchestrator[llamaindex]"
            )

    def plan(self, task: str) -> str:
        return task

    def execute(self, task: str, context: dict = None, policy=None) -> Any:
        if hasattr(self.agent, "chat"):
            res = self.agent.chat(task)
            if hasattr(res, "response"):
                self._extract_token_usage(res)
                return {"output": res.response}
            return res
        elif hasattr(self.agent, "query"):
            res = self.agent.query(task)
            if hasattr(res, "response"):
                return {"output": res.response}
            return res
        else:
            raise ValueError(
                "Object passed to LlamaIndexAdapter is not a valid LlamaIndex agent"
            )

    async def execute_async(self, task: str, context: dict = None, policy=None) -> Any:
        if hasattr(self.agent, "achat"):
            res = await self.agent.achat(task)
            if hasattr(res, "response"):
                self._extract_token_usage(res)
                return {"output": res.response}
            return res
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, lambda: self.execute(task, context, policy)
            )

    def _extract_token_usage(self, res: Any):
        # LlamaIndex doesn't consistently write token counts to the response object itself.
        # But we check for typical properties in custom setups.
        token_usage = getattr(res, "token_usage", None)
        if token_usage:
            self._token_usage = getattr(token_usage, "total_tokens", 0)

    def get_token_usage(self) -> int:
        return self._token_usage


# Register with central adapter registry
from oao.adapters.registry import AdapterRegistry

AdapterRegistry.register("llamaindex", LlamaIndexAdapter)
