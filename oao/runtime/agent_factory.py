from typing import Any


class AgentFactory:
    """
    Responsible for creating agents dynamically
    based on framework type.
    """

    @staticmethod
    def create_agent(framework: str) -> Any:
        """
        Extend this method to support
        different frameworks dynamically.
        """

        if framework == "langchain":
            return AgentFactory._create_langchain_agent()

        raise ValueError(f"Unsupported framework: {framework}")

    # -----------------------------------------------------

    @staticmethod
    def _create_langchain_agent():
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage
        except ImportError:
            try:
                 # Fallback for older versions or if user installed via langchain directly
                from langchain.chat_models import ChatOpenAI
                from langchain.schema import HumanMessage
            except ImportError:
                raise ImportError(
                    "LangChain is not installed.\n"
                    "Install it with:\n"
                    "    pip install open-agent-orchestrator[langchain]"
                )

        class LangChainSimpleAgent:
            def __init__(self):
                self.llm = ChatOpenAI()

            def invoke(self, task: str):
                response = self.llm.invoke([HumanMessage(content=task)])
                return {"output": response.content}

        return LangChainSimpleAgent()
