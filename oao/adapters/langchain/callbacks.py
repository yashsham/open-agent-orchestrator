from typing import Any, Dict, List, Optional
from uuid import UUID

try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
except ImportError:
    class BaseCallbackHandler:
        pass
    LLMResult = Any

from oao.runtime.event_bus import EventBus
from oao.runtime.events import Event, EventType

class OAOCallbackHandler(BaseCallbackHandler):
    """
    Callback Handler that emits OAO events for LangChain executions.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running."""
        self.event_bus.emit(Event(EventType.LLM_START, {"prompts": prompts}))

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        # Try to extract token usage
        token_usage = 0
        if hasattr(response, "llm_output") and response.llm_output:
            token_usage = response.llm_output.get("token_usage", {}).get("total_tokens", 0)
            
        self.event_bus.emit(Event(EventType.LLM_END, {"token_usage": token_usage}))

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Run when chain starts running."""
        pass # We track chain start via Orchestrator state

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Run when chain ends running."""
        pass

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Run when tool starts running."""
        self.event_bus.emit(Event(EventType.TOOL_START, {"input": input_str}))

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Run when tool ends running."""
        self.event_bus.emit(Event(EventType.TOOL_END, {"output": output}))

    def on_tool_error(
        self, error: BaseException, **kwargs: Any
    ) -> None:
        """Run when tool errors."""
        self.event_bus.emit(Event(EventType.TOOL_ERROR, {"error": str(error)}))
