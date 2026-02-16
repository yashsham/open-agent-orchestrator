from typing import Any

from oao.adapters.base_adapter import BaseAdapter
from oao.runtime.tool_wrapper import wrap_tool


class LangChainAdapter(BaseAdapter):
    """
    Adapter for LangChain-based agents or runnables.

    This adapter requires the optional dependency:
        pip install open-agent-orchestrator[langchain]
    """

    def __init__(self, agent: Any, session_id: str = None):
        self._ensure_langchain_installed()
        self.agent = agent
        self._token_usage = 0
        self.session_id = session_id
        
        # Inject memory if agent is a Runnable (modern LangChain)
        if self.session_id:
            from oao.adapters.langchain.memory import OAORedisChatMessageHistory
            from langchain_core.runnables.history import RunnableWithMessageHistory
            
            # If agent is already a Runnable binding, we wrap it
            # Note: This implies the agent expects 'input' and returns 'output' or similar dict
            self.agent_with_history = RunnableWithMessageHistory(
                agent,
                lambda session_id: OAORedisChatMessageHistory(session_id),
                input_messages_key="input",
                history_messages_key="history",
            )
        else:
            self.agent_with_history = None

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

        # Create callbacks
        from oao.adapters.langchain.callbacks import OAOCallbackHandler
        from oao.runtime.event_bus import EventBus
        
        event_bus = EventBus() 
        callback = OAOCallbackHandler(event_bus)

        config = {"callbacks": [callback]}
        if self.session_id:
            config["configurable"] = {"session_id": self.session_id}
            invoker = self.agent_with_history if self.agent_with_history else self.agent
        else:
            invoker = self.agent

        result = invoker.invoke(task, config=config)

        self._extract_token_usage(result)

        return result

    async def execute_async(self, task: str, context: dict = None, policy=None) -> Any:
        """
        Asynchronous execution.
        """

        import asyncio

        if context is not None:
            self._wrap_tools(context, policy)

        from oao.adapters.langchain.callbacks import OAOCallbackHandler
        from oao.runtime.event_bus import EventBus
        
        event_bus = EventBus()
        callback = OAOCallbackHandler(event_bus)
        
        config = {"callbacks": [callback]}
        if self.session_id:
            config["configurable"] = {"session_id": self.session_id}
            invoker = self.agent_with_history if self.agent_with_history else self.agent
        else:
            invoker = self.agent

        # If agent supports ainvoke, use it. Else run_in_executor.
        if hasattr(invoker, "ainvoke"):
            result = await invoker.ainvoke(task, config=config)
        else:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: invoker.invoke(task, config=config),
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
            if isinstance(result, dict):
                # Check standard dictionary result
                if "usage" in result:
                    usage = result.get("usage", {})
                    self._token_usage = usage.get("total_tokens", 0)
                # Check AIMessage-like logic (if result is object, handled below, but if dict representation)
                elif "response_metadata" in result:
                     meta = result.get("response_metadata", {})
                     token_usage = meta.get("token_usage", {})
                     self._token_usage = token_usage.get("total_tokens", 0) if isinstance(token_usage, dict) else token_usage.get("total_tokens", 0)

            # Handle AIMessage or other objects
            elif hasattr(result, "response_metadata"):
                meta = getattr(result, "response_metadata", {})
                token_usage = meta.get("token_usage", {})
                self._token_usage = token_usage.get("total_tokens", 0) if isinstance(token_usage, dict) else 0 # Handle non-dict
            
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
