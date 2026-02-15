from oao.plugins.base import PluginInterface
from oao.policy.registry import PolicyRegistry
from oao.runtime.events import GlobalEventRegistry, EventType
from oao.runtime.scheduler import SchedulerRegistry

# Custom Policy
class StrictJsonPolicy:
    def validate(self, context):
        print("[PLUGIN] Validating JSON policy...")

# Custom Scheduler
class FifoScheduler:
    def __init__(self, concurrency):
        self.concurrency = concurrency
    
    async def run(self, tasks):
        print(f"[PLUGIN] Running FIFO scheduler with concurrency {self.concurrency}")
        results = {}
        for name, task in tasks.items():
            results[name] = await task
        return results

# Custom Event Listener
def on_execution_complete(event):
    print(f"[PLUGIN] Execution completed: {event.payload.get('status')}")

class SamplePlugin(PluginInterface):
    @property
    def name(self) -> str:
        return "sample_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    def activate(self):
        print(f"[PLUGIN] Activating {self.name}...")
        
        # Register Policy
        PolicyRegistry.register("strict_json", StrictJsonPolicy)
        
        # Register Scheduler
        SchedulerRegistry.register("fifo", FifoScheduler)
        
        # Register Event Listener
        GlobalEventRegistry.register(EventType.EXECUTION_COMPLETE, on_execution_complete)

    def deactivate(self):
        print(f"[PLUGIN] Deactivating {self.name}...")
