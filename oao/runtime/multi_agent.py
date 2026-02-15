from typing import Dict, Any
import asyncio

from oao.runtime.orchestrator import Orchestrator
from oao.runtime.scheduler import ParallelAgentScheduler
from oao.policy.strict_policy import StrictPolicy


class MultiAgentOrchestrator:
    """
    Coordinates multiple agents using a controlled parallel scheduler.
    """

    def __init__(
        self,
        policy: StrictPolicy = None,
        max_concurrency: int = 3,
        scheduler_name: str = "default",
    ):
        self.policy = policy or StrictPolicy()
        
        # Use registry or fallback to default
        from oao.runtime.scheduler import SchedulerRegistry, ParallelAgentScheduler
        SchedulerClass = SchedulerRegistry.get(scheduler_name) or ParallelAgentScheduler
        self.scheduler = SchedulerClass(max_concurrency)

    async def run_multi_async(
        self,
        agents: Dict[str, Any],
        task: str,
        framework: str = "langchain",
    ):

        async_tasks = {}

        for name, agent in agents.items():

            async def agent_task(agent=agent):
                orch = Orchestrator(policy=self.policy)
                return await orch.run_async(agent, task, framework)

            async_tasks[name] = agent_task()

        results = await self.scheduler.run(async_tasks)

        return results

