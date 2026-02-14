import asyncio
from oao.runtime.multi_agent import MultiAgentOrchestrator


class DummyAgent:
    def __init__(self, name):
        self.name = name

    def invoke(self, task):
        return {"output": f"{self.name} processed: {task}"}


async def main():

    agents = {
        f"agent_{i}": DummyAgent(f"Agent-{i}")
        for i in range(10)
    }

    multi_orch = MultiAgentOrchestrator(max_concurrency=2)

    results = await multi_orch.run_multi_async(
        agents=agents,
        task="Discuss AI governance",
    )

    for name, report in results.items():
        print(name, report.status)


asyncio.run(main())


