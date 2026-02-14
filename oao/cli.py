import argparse
import json
import os

from oao.runtime.orchestrator import Orchestrator
from oao.policy.strict_policy import StrictPolicy
from dotenv import load_dotenv
import oao.adapters.langchain_adapter # Register adapter


def run_command():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="OpenAgentOrchestrator CLI"
    )

    parser.add_argument(
        "--framework",
        type=str,
        default="langchain",
        help="Framework adapter to use (default: langchain)",
    )

    parser.add_argument(
        "--task",
        type=str,
        required=True,
        help="Task prompt for the agent",
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=10,
        help="Maximum execution steps",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4000,
        help="Maximum token limit",
    )

    args = parser.parse_args()

    # Basic policy
    policy = StrictPolicy(
        max_steps=args.max_steps,
        max_tokens=args.max_tokens,
    )

    # Simple LangChain agent example
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    class SimpleAgent:
        def __init__(self):
            self.llm = ChatOpenAI()

        def invoke(self, task: str):
            response = self.llm.invoke([HumanMessage(content=task)])
            return {"output": response.content}

    agent = SimpleAgent()

    orchestrator = Orchestrator(policy=policy)

    report = orchestrator.run(
        agent=agent,
        task=args.task,
        framework=args.framework,
    )

    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    run_command()
