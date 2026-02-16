import time
import asyncio
import statistics
from typing import Any
from oao.runtime.orchestrator import Orchestrator
from oao.runtime.event_store import InMemoryEventStore
from oao.runtime.persistence import InMemoryPersistenceAdapter

class BenchmarkAgent:
    def __init__(self, steps: int = 5):
        self.steps = steps
        self.current = 0

    def plan(self, task: str): return task
    
    def execute(self, task: str, context: dict = None, policy = None):
        self.current += 1
        # Minimal work to isolate OAO overhead
        return f"Step {self.current} done"

    async def execute_async(self, task: str, context: dict = None, policy = None):
        return self.execute(task, context, policy)

    def invoke(self, input_data: Any, config: Any = None):
        return self.execute(input_data)

    async def ainvoke(self, input_data: Any, config: Any = None):
        return await self.execute_async(input_data)

    def is_terminal(self):
        return self.current >= self.steps

async def run_benchmark(iterations: int = 10, steps_per_run: int = 10):
    print(f"Starting OAO Runtime Benchmark ({iterations} runs, {steps_per_run} steps each)")
    print("-" * 50)
    
    latencies = []
    
    for i in range(iterations):
        agent = BenchmarkAgent(steps=steps_per_run)
        # We reuse StateMachine and other components for isolation
        # but create a fresh orchestrator to avoid state carryover
        orchestrator = Orchestrator(
            persistence=InMemoryPersistenceAdapter(),
            event_store=InMemoryEventStore()
        )
        
        start_time = time.perf_counter()
        await orchestrator.run_async(agent, "benchmark_task")
        end_time = time.perf_counter()
        
        total_time = (end_time - start_time) * 1000 # ms
        latencies.append(total_time)
        print(f"Run {i+1}: {total_time:.2f}ms Total ({total_time/steps_per_run:.2f}ms per step)")

    avg = statistics.mean(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18] # 95th percentile
    
    print("-" * 50)
    print(f"AVG Total Latency: {avg:.2f}ms")
    print(f"AVG Step Overhead: {avg/steps_per_run:.2f}ms")
    print(f"P95 Total Latency: {p95:.2f}ms")
    print("-" * 50)
    print("NOTE: Benchmark run on In-Memory adapters. Redis will add network RTT.")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
