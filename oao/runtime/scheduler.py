import asyncio
from typing import Dict, Any, Callable


class ParallelAgentScheduler:
    """
    Controls concurrent execution of multiple agents.
    """

    def __init__(self, max_concurrency: int = 3):
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def _run_with_limit(self, coro: Callable):
        async with self._semaphore:
            return await coro

    async def run(
        self,
        tasks: Dict[str, Callable],
    ) -> Dict[str, Any]:

        results = {}

        async def execute(name, coro):
            try:
                result = await self._run_with_limit(coro)
                results[name] = result
            except Exception as e:
                results[name] = {"error": str(e)}

        await asyncio.gather(
            *(execute(name, task) for name, task in tasks.items())
        )

        return results
