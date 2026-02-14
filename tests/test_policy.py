import pytest
from oao.runtime.orchestrator import Orchestrator
from oao.policy.strict_policy import StrictPolicy


class DummyAgent:
    def invoke(self, task):
        return {"output": f"Processed: {task}"}


def test_policy_step_limit():

    policy = StrictPolicy(max_steps=1)
    orch = Orchestrator(policy=policy)

    report = orch.run(
        agent=DummyAgent(),
        task="Test policy",
        framework="langchain",
    )
    
    # Note: Depending on implementation, max_steps=1 might allow init->plan->execute (3 steps?) 
    # or strict step counting. 
    # If the orchestrator runs INIT, PLAN, EXECUTE, REVIEW, TERMINATE... that's 5 transitions.
    # But step count usually increments on EXECUTE.
    # Let's verify what StrictPolicy enforces. 
    # If max_steps=1, it should fail if it tries to go beyond.
    # However, if the agent finishes in 1 step, it might be SUCCESS.
    # The user provided test says assert report.status == "FAILED".
    # I will paste the code as requested, but I might need to adjust max_steps if the logic differs.
    # For now, trusting the user's snippet.

    assert report.status == "FAILED"
