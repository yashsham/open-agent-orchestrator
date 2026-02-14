import pytest
from oao.runtime.orchestrator import Orchestrator
from oao.policy.strict_policy import StrictPolicy


class DummyAgent:
    def invoke(self, task):
        return {"output": f"Processed: {task}"}


def test_orchestrator_success():

    policy = StrictPolicy(max_steps=5)
    orch = Orchestrator(policy=policy)

    report = orch.run(
        agent=DummyAgent(),
        task="Test task",
    )

    assert report.status == "SUCCESS"
    assert report.total_steps > 0
    assert report.final_output is not None
