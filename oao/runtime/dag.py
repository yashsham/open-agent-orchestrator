"""
DAG-Based Orchestration for Complex Workflows

This module enables directed acyclic graph (DAG) execution for workflows
with task dependencies, allowing parallel execution of independent tasks.
"""

from typing import Any, Dict, List, Set, Optional
from collections import defaultdict, deque
import asyncio

from oao.runtime.orchestrator import Orchestrator
from oao.runtime.scheduler import ParallelAgentScheduler


class TaskNode:
    """
    Represents a single task in a workflow graph.
    
    Each task has a unique name, an agent to execute it, and a list
    of dependencies (task names that must complete first).
    """
    
    def __init__(
        self,
        name: str,
        agent: Any,
        dependencies: Optional[List[str]] = None
    ):
        """
        Initialize a task node.
        
        Args:
            name: Unique task identifier
            agent: Agent instance to execute this task
            dependencies: List of task names this task depends on
        """
        self.name = name
        self.agent = agent
        self.dependencies = dependencies or []
        self.result: Optional[Any] = None
    
    def __repr__(self):
        return f"TaskNode(name='{self.name}', deps={self.dependencies})"


class TaskGraph:
    """
    Container for a directed acyclic graph (DAG) of tasks.
    
    Manages task nodes and provides validation and execution ordering.
    """
    
    def __init__(self):
        """Initialize an empty task graph."""
        self.nodes: Dict[str, TaskNode] = {}
    
    def add_node(self, node: TaskNode):
        """
        Add a task node to the graph.
        
        Args:
            node: TaskNode to add
            
        Raises:
            ValueError: If a node with the same name already exists
        """
        if node.name in self.nodes:
            raise ValueError(f"Node '{node.name}' already exists in graph")
        
        self.nodes[node.name] = node
    
    def validate(self):
        """
        Validate the graph structure.
        
        Checks for:
        - Missing dependencies
        - Circular dependencies (cycles)
        
        Raises:
            ValueError: If validation fails
        """
        # Check for missing dependencies
        for node_name, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    raise ValueError(
                        f"Node '{node_name}' depends on '{dep}', "
                        f"which doesn't exist in graph"
                    )
        
        # Check for cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node_name: str) -> bool:
            visited.add(node_name)
            rec_stack.add(node_name)
            
            for dep in self.nodes[node_name].dependencies:
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(node_name)
            return False
        
        for node_name in self.nodes:
            if node_name not in visited:
                if has_cycle(node_name):
                    raise ValueError(f"Graph contains a cycle involving '{node_name}'")
    
    def get_execution_order(self) -> List[List[str]]:
        """
        Get the topological execution order of tasks.
        
        Uses Kahn's algorithm to produce a level-by-level ordering,
        where tasks at the same level can be executed in parallel.
        
        Returns:
            List of levels, where each level is a list of task names
            that can be executed concurrently
            
        Raises:
            ValueError: If graph contains cycles
        """
        # Calculate in-degree for each node
        in_degree = {name: 0 for name in self.nodes}
        adj_list = defaultdict(list)
        
        for node_name, node in self.nodes.items():
            for dep in node.dependencies:
                adj_list[dep].append(node_name)
                in_degree[node_name] += 1
        
        # Initialize queue with nodes that have no dependencies
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        
        execution_order = []
        processed_count = 0
        
        while queue:
            # All nodes in current queue can be executed in parallel
            level = []
            level_size = len(queue)
            
            for _ in range(level_size):
                node_name = queue.popleft()
                level.append(node_name)
                processed_count += 1
                
                # Reduce in-degree for dependent nodes
                for neighbor in adj_list[node_name]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
            
            execution_order.append(level)
        
        # Check if all nodes were processed (no cycles)
        if processed_count != len(self.nodes):
            raise ValueError("Graph contains a cycle")
        
        return execution_order
    
    def get_node(self, name: str) -> TaskNode:
        """Get a node by name."""
        if name not in self.nodes:
            raise ValueError(f"Node '{name}' not found in graph")
        return self.nodes[name]


class GraphExecutor:
    """
    Executes a TaskGraph with dependency-aware parallel execution.
    
    Uses topological sorting to determine execution order and runs
    independent tasks concurrently using ParallelAgentScheduler.
    """
    
    def __init__(
        self,
        graph: TaskGraph,
        policy: Optional[Any] = None,
        max_concurrency: int = 3
    ):
        """
        Initialize graph executor.
        
        Args:
            graph: TaskGraph to execute
            policy: Optional policy for orchestration
            max_concurrency: Maximum concurrent tasks
        """
        self.graph = graph
        self.policy = policy
        self.scheduler = ParallelAgentScheduler(max_concurrency=max_concurrency)
        
        # Validate graph on initialization
        self.graph.validate()
    
    def execute(self, task: str, framework: str = "langchain") -> Dict[str, Any]:
        """
        Execute the graph synchronously.
        
        Args:
            task: Task description to pass to all agents
            framework: Framework type for agent creation
            
        Returns:
            Dictionary mapping task names to execution reports
        """
        # This is a sync wrapper around async implementation
        import asyncio
        return asyncio.run(self.execute_async(task, framework))
    
    async def execute_async(
        self,
        task: str,
        framework: str = "langchain"
    ) -> Dict[str, Any]:
        """
        Execute the graph asynchronously.
        
        Args:
            task: Task description to pass to all agents
            framework: Framework type for agent creation
            
        Returns:
            Dictionary mapping task names to execution reports
        """
        # Get execution order (levels)
        execution_order = self.graph.get_execution_order()
        
        results = {}
        
        # Execute level by level
        for level in execution_order:
            # Build tasks for this level
            level_tasks = {}
            
            for task_name in level:
                node = self.graph.get_node(task_name)
                
                # Gather dependency results
                dep_results = {
                    dep: self.graph.get_node(dep).result
                    for dep in node.dependencies
                }
                
                # Create orchestrator for this task
                async def execute_task(node=node, dep_results=dep_results):
                    orch = Orchestrator(policy=self.policy)
                    
                    # Augment task with dependency context
                    augmented_task = task
                    if dep_results:
                        context_str = "\n\nContext from previous tasks:\n"
                        for dep_name, dep_result in dep_results.items():
                            if hasattr(dep_result, 'final_output'):
                                context_str += f"- {dep_name}: {dep_result.final_output}\n"
                        augmented_task = task + context_str
                    
                    report = await orch.run_async(
                        agent=node.agent,
                        task=augmented_task,
                        framework=framework
                    )
                    
                    # Store result in node
                    node.result = report
                    return report
                
                level_tasks[task_name] = execute_task()
            
            # Execute all tasks in this level concurrently
            level_results = await self.scheduler.run(level_tasks)
            results.update(level_results)
        
        return results
