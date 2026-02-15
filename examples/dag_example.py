"""
DAG-Based Orchestration Example

Demonstrates a complex workflow using DAG:
    Research → Summarize
            → Critic → Improve

This shows how independent tasks (Summarize, Critic) can run in parallel
after Research completes, then both feed into Improve.
"""

import asyncio
import time
from oao.runtime.dag import TaskNode, TaskGraph, GraphExecutor


class TimedAgent:
    """
    Mock agent that simulates processing time.
    Used to demonstrate parallel execution.
    """
    
    def __init__(self, name: str, processing_time: float = 0.5):
        self.name = name
        self.processing_time = processing_time
    
    def invoke(self, task: str):
        """Simulate agent processing with delay."""
        print(f"  🤖 {self.name} started at {time.strftime('%H:%M:%S')}")
        time.sleep(self.processing_time)
        result = f"{self.name} completed: {task}"
        print(f"  ✅ {self.name} finished at {time.strftime('%H:%M:%S')}")
        return {"output": result}


def build_research_workflow():
    """
    Build a research workflow DAG:
    
        Research
        ├─→ Summarize
        └─→ Critic
            └─→ Improve ←──┘
    
    - Research runs first
    - Summarize and Critic run in parallel (both depend on Research)
    - Improve runs last (depends on both Summarize and Critic)
    """
    print("\n📊 Building DAG Workflow...")
    print("=" * 60)
    
    graph = TaskGraph()
    
    # Create task nodes
    research = TaskNode(
        name="Research",
        agent=TimedAgent("Researcher", processing_time=1.0)
    )
    
    summarize = TaskNode(
        name="Summarize",
        agent=TimedAgent("Summarizer", processing_time=0.8),
        dependencies=["Research"]
    )
    
    critic = TaskNode(
        name="Critic",
        agent=TimedAgent("Critic", processing_time=0.8),
        dependencies=["Research"]
    )
    
    improve = TaskNode(
        name="Improve",
        agent=TimedAgent("Improver", processing_time=0.6),
        dependencies=["Summarize", "Critic"]
    )
    
    # Add nodes to graph
    graph.add_node(research)
    graph.add_node(summarize)
    graph.add_node(critic)
    graph.add_node(improve)
    
    print("✅ DAG Structure:")
    print("   Research → Summarize")
    print("           → Critic → Improve")
    print("=" * 60)
    
    return graph


def display_execution_plan(graph: TaskGraph):
    """Display the execution plan with parallelism."""
    print("\n📋 Execution Plan (Topological Sort):")
    print("=" * 60)
    
    execution_order = graph.get_execution_order()
    
    for level_num, level in enumerate(execution_order, 1):
        if len(level) == 1:
            print(f"  Level {level_num}: {level[0]}")
        else:
            print(f"  Level {level_num}: {', '.join(level)} (parallel)")
    
    print("=" * 60)


async def execute_workflow(graph: TaskGraph, task: str):
    """Execute the DAG workflow."""
    print(f"\n🚀 Executing Workflow: '{task}'")
    print("=" * 60)
    
    start_time = time.time()
    
    # Create executor
    executor = GraphExecutor(graph, max_concurrency=3)
    
    # Execute
    results = await executor.execute_async(task, framework="langchain")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print("=" * 60)
    print(f"\n✨ Workflow Complete!")
    print(f"   Total time: {total_time:.2f}s")
    
    # Calculate sequential time
    sequential_time = sum([
        1.0,  # Research
        0.8,  # Summarize
        0.8,  # Critic
        0.6,  # Improve
    ])
    
    speedup = sequential_time / total_time
    print(f"   Sequential time would be: {sequential_time:.2f}s")
    print(f"   Speedup: {speedup:.2f}x")
    
    return results


def display_results(results: dict):
    """Display execution results."""
    print("\n📊 Task Results:")
    print("=" * 60)
    
    for task_name, result in results.items():
        status = getattr(result, 'status', 'unknown')
        output = getattr(result, 'final_output', 'no output')
        
        print(f"  {task_name}:")
        print(f"    Status: {status}")
        if hasattr(result, 'final_output'):
            print(f"    Output: {output[:100]}...")
    
    print("=" * 60)


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("🌟 DAG-Based Orchestration Demo")
    print("=" * 60)
    
    # Build the workflow
    graph = build_research_workflow()
    
    # Display execution plan
    display_execution_plan(graph)
    
    # Execute
    task = "Analyze the impact of AI on software development"
    results = asyncio.run(execute_workflow(graph, task))
    
    # Display results
    display_results(results)
    
    print("\n💡 Key Observations:")
    print("  • Research runs first (no dependencies)")
    print("  • Summarize & Critic run in parallel (both depend on Research)")
    print("  • Improve runs last (depends on both Summarize & Critic)")
    print("  • Total time < sum of all tasks due to parallelism")
    print("=" * 60)


if __name__ == "__main__":
    main()
