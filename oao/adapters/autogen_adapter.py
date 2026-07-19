from typing import Any, Dict, Optional
import asyncio

from oao.adapters.base_adapter import BaseAdapter


class AutoGenAdapter(BaseAdapter):
    """
    Adapter for Microsoft AutoGen-based agents (ConversableAgent, UserProxyAgent, etc.).
    """

    def __init__(self, sender_agent: Any):
        self._ensure_autogen_installed()
        self.sender_agent = sender_agent
        self._token_usage = 0

    def _ensure_autogen_installed(self):
        try:
            import autogen  # noqa: F401
        except ImportError:
            raise ImportError(
                "AutoGen is not installed.\n"
                "Install it with:\n"
                "    pip install open-agent-orchestrator[autogen]"
            )

    def plan(self, task: str) -> str:
        return task

    def execute(self, task: str, context: dict = None, policy=None) -> Any:
        recipient = None
        message = task

        if isinstance(task, dict):
            recipient = task.get("recipient")
            message = task.get("message", "")

        if not recipient and context:
            recipient = context.get("recipient") or context.get("agent")

        if not recipient:
            raise ValueError(
                "AutoGen execution requires a 'recipient' agent. Provide it in the task dict or context."
            )

        chat_res = self.sender_agent.initiate_chat(
            recipient=recipient, message=message
        )
        self._extract_token_usage(chat_res)

        if hasattr(chat_res, "summary"):
            return {
                "output": chat_res.summary,
                "chat_history": getattr(chat_res, "chat_history", None),
            }
        return chat_res

    async def execute_async(self, task: str, context: dict = None, policy=None) -> Any:
        recipient = None
        message = task

        if isinstance(task, dict):
            recipient = task.get("recipient")
            message = task.get("message", "")

        if not recipient and context:
            recipient = context.get("recipient") or context.get("agent")

        if not recipient:
            raise ValueError(
                "AutoGen execution requires a 'recipient' agent. Provide it in the task dict or context."
            )

        if hasattr(self.sender_agent, "a_initiate_chat"):
            chat_res = await self.sender_agent.a_initiate_chat(
                recipient=recipient, message=message
            )
            self._extract_token_usage(chat_res)
            if hasattr(chat_res, "summary"):
                return {
                    "output": chat_res.summary,
                    "chat_history": getattr(chat_res, "chat_history", None),
                }
            return chat_res
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, lambda: self.execute(task, context, policy)
            )

    def _extract_token_usage(self, chat_res: Any):
        cost = getattr(chat_res, "cost", None)
        if cost and isinstance(cost, dict):
            total_tokens = cost.get("usage_including_cached_inference", {}).get(
                "total_tokens", 0
            )
            if not total_tokens:
                total_tokens = sum(
                    v.get("total_tokens", 0)
                    for v in cost.values()
                    if isinstance(v, dict)
                )
            self._token_usage = total_tokens

    def get_token_usage(self) -> int:
        return self._token_usage


# Register with central adapter registry
from oao.adapters.registry import AdapterRegistry

AdapterRegistry.register("autogen", AutoGenAdapter)
