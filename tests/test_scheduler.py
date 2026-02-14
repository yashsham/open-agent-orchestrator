import asyncio
import pytest
from oao.runtime.scheduler import ParallelAgentScheduler


@pytest.mark.asyncio
async def test_scheduler_runs_tasks():

    scheduler = ParallelAgentScheduler(max_concurrency=2)

    async def dummy_task():
        await asyncio.sleep(0.1)
        return "done"

    tasks = {
        "task1": dummy_task(),
        "task2": dummy_task(),
        "task3": dummy_task(),
    }

    results = await scheduler.run(tasks)

    assert len(results) == 3
    assert all(value == "done" for value in results.values())
