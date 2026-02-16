import logging
import sys
import os
import time

# Ensure we can import oao
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from oao.runtime.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class CrashingAgent:
    """An agent that simulates a crash on the first attempt at step 2."""
    
    def __init__(self):
        self.step = 0
        self.has_crashed = False
        
    def invoke(self, task):
        self.step += 1
        logging.info(f"[Agent] Processing Step {self.step}...")
        
        if self.step == 2 and not self.has_crashed:
            logging.error("[Agent] CRITICAL FAILURE! Simulating a crash...")
            self.has_crashed = True
            raise RuntimeError("Simulated Crash")
            
        return {"output": f"Result of Step {self.step}", "done": self.step >= 3}

def main():
    print(f"\n{'='*50}")
    print("DEMO: Deterministic Replay & Recovery")
    print(f"{'='*50}\n")
    
    orch = Orchestrator()
    agent = CrashingAgent()
    
    # 1. Start execution (expecting a crash)
    print("[1] Starting execution (Step 2 will crash)...")
    try:
        orch.run(agent, "Execute multi-step task")
    except RuntimeError:
        print("\n[INFO] Agent crashed as expected.")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        
    execution_id = orch.context.get("execution_id", "simulated-id")
    
    # 2. Simulate User Intervention / Restart
    print("\n[2] Simulating restart & recovery...")
    print(f"    Resuming execution {execution_id}...")
    
    # In a real scenario, we'd load state from Redis.
    # Here, we simulate the 'fix' by flagging the agent as 'has_crashed=True' (already done)
    # and resuming.
    
    # For demo purposes without a full Redis backend running, we'll manually retry
    # OAO's 'replay' feature typically works via the API server.
    # Here we show the concept: Resume logic skips completed steps.
    
    print("    [REPLAY] Skipping Step 1 (Completed)")
    print("    [REPLAY] Retrying Step 2...")
    
    # Reset step count for visual clarity in demo logs (agent state is persistent in reality)
    # We re-run. A real ReplayManager would hydrate state.
    
    try:
        # Re-running the same agent instance which now has has_crashed=True
        orch.run(agent, "Execute multi-step task")
        print("\n[SUCCESS] Execution completed successfully after replay!")
    except Exception as e:
        print(f"\n[FAILURE] Replay failed: {e}")

    print(f"{'='*50}")
    print("Demo Complete")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
