from typing import Any, Dict, Optional

from oao.adapters.base_adapter import BaseAdapter
from oao.runtime.tool_wrapper import wrap_tool

class LangGraphAdapter(BaseAdapter):
    """
    Adapter for LangGraph-based agents (StateGraph/CompiledGraph).
    
    This adapter requires the optional dependency:
        pip install open-agent-orchestrator[langgraph]
    """

    def __init__(self, graph: Any):
        self._ensure_langgraph_installed()
        self.graph = graph
        self._token_usage = 0

    def _ensure_langgraph_installed(self):
        try:
            import langgraph  # noqa: F401
        except ImportError:
            raise ImportError(
                "LangGraph is not installed.\n"
                "Install it with:\n"
                "    pip install open-agent-orchestrator[langgraph]"
            )

    # =====================================================
    # Lifecycle Methods
    # =====================================================

    def plan(self, task: str) -> str:
        # LangGraph handles planning internally via graph structure
        return task

    def execute(self, task: str, context: dict = None, policy=None) -> Any:
        # LangGraph inputs can be complex.
        # If task is a string, we try to form a standard "messages" input.
        if isinstance(task, str):
            # Try standard LangGraph pattern: {"messages": [HumanMessage(...)]}
            # But we avoid importing HumanMessage if possible.
            # Many graphs accept raw dicts representing messages.
            inputs = {"messages": [{"role": "user", "content": task}]}
        elif isinstance(task, dict):
            inputs = task
        else:
            inputs = {"input": task}

        from oao.adapters.langchain.callbacks import OAOCallbackHandler
        from oao.runtime.event_bus import EventBus
        
        event_bus = EventBus() 
        callback = OAOCallbackHandler(event_bus)
        
        # Invoke graph
        # config is where callbacks go
        result = self.graph.invoke(inputs, config={"callbacks": [callback]})
        
        self._extract_token_usage(result)
        
        return result

    async def execute_async(self, task: str, context: dict = None, policy=None) -> Any:
        
        if isinstance(task, str):
             inputs = {"messages": [{"role": "user", "content": task}]}
        elif isinstance(task, dict):
            inputs = task
        else:
            inputs = {"input": task}

        from oao.adapters.langchain.callbacks import OAOCallbackHandler
        from oao.runtime.event_bus import EventBus
        
        event_bus = EventBus()
        callback = OAOCallbackHandler(event_bus)
        
        result = await self.graph.ainvoke(inputs, config={"callbacks": [callback]})
        
        self._extract_token_usage(result)
        
        return result

    def _extract_token_usage(self, result: Any):
        # LangGraph results are typically the final state.
        # Token usage capture depends on where it's stored in state.
        # Standardize on looking for "usage" key or similar?
        # For now, simplistic approach similar to LC adapter.
        pass

    def get_token_usage(self) -> int:
        return self._token_usage

# =====================================================
# Adapter Registration
# =====================================================

from oao.adapters.registry import AdapterRegistry

AdapterRegistry.register("langgraph", LangGraphAdapter)
