from typing import Any, Dict, Optional
import asyncio

from oao.adapters.base_adapter import BaseAdapter


class AgnoAdapter(BaseAdapter):
    """
    Adapter for Agno AI (formerly Phidata) agent objects.
    """

    def __init__(self, agent: Any):
        self._ensure_agno_installed()
        self.agent = agent
        self._token_usage = 0

    def _ensure_agno_installed(self):
        try:
            try:
                import agno  # noqa: F401
            except ImportError:
                import phidata  # noqa: F401
        except ImportError:
            raise ImportError(
                "Agno (or Phidata) is not installed.\n"
                "Install it with:\n"
                "    pip install open-agent-orchestrator[agno]"
            )

    def plan(self, task: str) -> str:
        return task

    def execute(self, task: str, context: dict = None, policy=None) -> Any:
        res = self.agent.run(task)
        self._extract_token_usage(res)

        if hasattr(res, "content"):
            return {
                "output": res.content,
                "metrics": getattr(res, "metrics", None),
            }
        return res

    async def execute_async(self, task: str, context: dict = None, policy=None) -> Any:
        if hasattr(self.agent, "arun"):
            res = await self.agent.arun(task)
            self._extract_token_usage(res)
            if hasattr(res, "content"):
                return {
                    "output": res.content,
                    "metrics": getattr(res, "metrics", None),
                }
            return res
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, lambda: self.execute(task, context, policy)
            )

    def _extract_token_usage(self, res: Any):
        metrics = getattr(res, "metrics", None)
        if metrics:
            self._token_usage = getattr(metrics, "total_tokens", 0)

    def get_token_usage(self) -> int:
        return self._token_usage


# Register with central adapter registry
from oao.adapters.registry import AdapterRegistry

AdapterRegistry.register("agno", AgnoAdapter)
