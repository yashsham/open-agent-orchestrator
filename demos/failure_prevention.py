import logging
import sys
import os

# Ensure we can import oao
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from oao.runtime.orchestrator import Orchestrator
from oao.policy.strict_policy import StrictPolicy, PolicyViolation

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class GreedyAgent:
    """An agent that aggressively consumes tokens."""
    
    def __init__(self, name="GreedyBot"):
        self.name = name
    
    def invoke(self, task):
        # Simulate a verbose response with high token usage
        token_count = 5000
        logging.info(f"[{self.name}] Generating verbose response... ({token_count} tokens)")
        return {
            "output": "A" * 100,  # truncated content
            "usage": {"total_tokens": token_count}
        }

def main():
    print(f"\n{'='*50}")
    print("DEMO: Failure Prevention via StrictPolicy")
    print(f"{'='*50}\n")
    
    # 1. Define a strict policy with a low token limit
    print("[1] Configuring StrictPolicy (max_tokens=4000)...")
    policy = StrictPolicy(
        max_tokens=4000,
        max_steps=5,
        execution_timeout=10
    )
    
    # 2. Initialize Orchestrator
    print("[2] Initializing Orchestrator...")
    orch = Orchestrator(policy=policy)
    
    # 3. Run the greedy agent
    print("[3] Launching GreedyAgent (attempts to use 5000 tokens)...")
    agent = GreedyAgent()
    
    try:
        orch.run(agent, "Generate a very long report")
    except PolicyViolation as e:
        print(f"\n[SUCCESS] Orchestrator successfully blocked the agent!")
        print(f"Reason: {e}\n")
    except Exception as e:
        print(f"\n[ERROR] Unexpected exception: {e}\n")
        
    print(f"{'='*50}")
    print("Demo Complete")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
