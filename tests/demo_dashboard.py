import asyncio
import uuid
import httpx
from oao.runtime.orchestrator import Orchestrator
from oao.policy.strict_policy import StrictPolicy

class MockAgent:
    def __init__(self, name, steps=3, error_at=None):
        self.name = name
        self.steps = steps
        self.error_at = error_at
        self.current = 0

    async def ainvoke(self, task, context=None, policy=None):
        self.current += 1
        await asyncio.sleep(0.5) # Simulate work
        
        if self.error_at == self.current:
            raise ValueError(f"Simulated error in {self.name} at step {self.current}")
            
        return {
            "output": f"{self.name} step {self.current} done",
            "token_usage": 100
        }

async def run_demo_scenarios():
    print("Starting Dashboard Demo Scenarios...")
    
    # Scene 1: Happy Path
    print("  - Scenario 1: Successful 3-step execution")
    orch1 = Orchestrator()
    await orch1.run_async(MockAgent("SuccessBot", steps=3), "Finish task A")
    
    await asyncio.sleep(2)
    
    # Scene 2: Failure Path
    print("  - Scenario 2: Failure at step 2")
    orch2 = Orchestrator()
    try:
        await orch2.run_async(MockAgent("BuggyBot", steps=3, error_at=2), "Finish task B")
    except Exception:
        pass
        
    await asyncio.sleep(2)
    
    # Scene 3: Policy Violation
    print("  - Scenario 3: Policy Violation (Max Steps)")
    policy = StrictPolicy(max_steps=2)
    orch3 = Orchestrator(policy=policy)
    try:
        # Agent wants 5 steps, policy allows 2
        await orch3.run_async(MockAgent("RunawayBot", steps=5), "Recursive loop task")
    except Exception as e:
        print(f"    Expected Violation: {e}")

    print("\nDemo scenarios completed. Check your dashboard!")

if __name__ == "__main__":
    # Ensure server is running or this will just run locally without WS broadcast
    # unless GlobalEventRegistry is imported by the server process.
    # We'll run this to see if it triggers the GlobalEventRegistry listeners.
    asyncio.run(run_demo_scenarios())
