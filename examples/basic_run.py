from dotenv import load_dotenv
from oao.runtime.orchestrator import Orchestrator
from oao.policy.strict_policy import StrictPolicy
from oao.adapters.registry import AdapterRegistry

load_dotenv()


from oao.adapters.base_adapter import BaseAdapter

class DummyAdapter(BaseAdapter):
    def plan(self, task: str):
        return f"Plan for: {task}"


    def execute(self, task: str, context: dict = None, policy = None):
        return {"output": f"Executed: {task}"}

    def get_token_usage(self) -> int:
        return 100

adapter = DummyAdapter()
policy = StrictPolicy(max_steps=5)

orch = Orchestrator(policy=policy)
report = orch.run(agent=adapter, task="Explain AI orchestration")

print(report.model_dump_json(indent=2))
print(AdapterRegistry.list_adapters())

