import asyncio

from oao.runtime.orchestrator import Orchestrator
from oao.policy.strict_policy import StrictPolicy


class DummyAgent:
    def invoke(self, task: str):
        return {"output": f"Processed: {task}"}


async def main():
    orch = Orchestrator(policy=StrictPolicy())
    report = await orch.run_async(
        agent=DummyAgent(),
        task="Test async",
    )

    print(report.model_dump_json(indent=2))


asyncio.run(main())
