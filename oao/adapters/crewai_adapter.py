from typing import Any, Dict, Optional
import asyncio

from oao.adapters.base_adapter import BaseAdapter


class CrewAIAdapter(BaseAdapter):
    """
    Adapter for CrewAI-based agents (Crews or individual Agents).
    """

    def __init__(self, crew_or_agent: Any):
        self._ensure_crewai_installed()
        self.crew_or_agent = crew_or_agent
        self._token_usage = 0

    def _ensure_crewai_installed(self):
        try:
            import crewai  # noqa: F401
        except ImportError:
            raise ImportError(
                "CrewAI is not installed.\n"
                "Install it with:\n"
                "    pip install open-agent-orchestrator[crewai]"
            )

    def plan(self, task: str) -> str:
        # CrewAI manages task mapping/planning internally within tasks/crews
        return task

    def execute(self, task: str, context: dict = None, policy=None) -> Any:
        inputs = {"task": task} if isinstance(task, str) else (task or {})

        if hasattr(self.crew_or_agent, "kickoff"):
            # It is a Crew object
            result = self.crew_or_agent.kickoff(inputs=inputs)
            self._extract_token_usage(result)
            if hasattr(result, "raw"):
                return {
                    "output": result.raw,
                    "metrics": getattr(result, "token_usage", None),
                }
            return result
        elif hasattr(self.crew_or_agent, "execute_task"):
            # It is an individual Agent object
            result = self.crew_or_agent.execute_task(task, context=context)
            return {"output": result}
        else:
            raise ValueError(
                "Object passed to CrewAIAdapter is neither a Crew nor an Agent"
            )

    async def execute_async(self, task: str, context: dict = None, policy=None) -> Any:
        inputs = {"task": task} if isinstance(task, str) else (task or {})

        if hasattr(self.crew_or_agent, "kickoff_async"):
            result = await self.crew_or_agent.kickoff_async(inputs=inputs)
            self._extract_token_usage(result)
            if hasattr(result, "raw"):
                return {
                    "output": result.raw,
                    "metrics": getattr(result, "token_usage", None),
                }
            return result
        else:
            # Fallback to executing in executor thread
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, lambda: self.execute(task, context, policy)
            )

    def _extract_token_usage(self, result: Any):
        token_usage = getattr(result, "token_usage", None)
        if token_usage:
            self._token_usage = getattr(token_usage, "total_tokens", 0)

    def get_token_usage(self) -> int:
        return self._token_usage


# Register with central adapter registry
from oao.adapters.registry import AdapterRegistry

AdapterRegistry.register("crewai", CrewAIAdapter)
