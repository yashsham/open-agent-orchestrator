try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    raise ImportError(
        "FastAPI is not installed.\n"
        "Install with:\n"
        "    pip install open-agent-orchestrator[server]"
    )

import uuid
from typing import Dict, Optional

from oao.runtime.orchestrator import Orchestrator
from oao.runtime.multi_agent import MultiAgentOrchestrator
from oao.runtime.agent_factory import AgentFactory
from oao.policy.strict_policy import StrictPolicy
import oao.metrics as metrics
from prometheus_client import generate_latest
from fastapi import Response, WebSocket, WebSocketDisconnect
import json
from oao.runtime.event_bus import EventBus
from oao.runtime.events import Event, EventType

# -----------------------------------------------------
# Connection Manager for WebSockets
# -----------------------------------------------------

class ConnectionManager:
    """
    Manages active WebSocket connections for real-time telemetry.
    """
    def __init__(self):
        # Dict[execution_id, List[WebSocket]] or just List[WebSocket]
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_event(self, event: Event):
        """
        Broadcast an OAO event to all connected dashboard clients.
        """
        message = {
            "type": event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
            "data": event.to_dict() if hasattr(event, "to_dict") else str(event)
        }
        print(f"[WS] Broadcasting event: {message['type']} to {len(self.active_connections)} clients")
        
        # We need to serialize some things if they aren't JSON safe
        # ExecutionEvent should have .to_dict()
        
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected_clients.append(connection)
        
        for client in disconnected_clients:
            self.active_connections.remove(client)

manager = ConnectionManager()

# Bridge EventBus to WebSocket Manager
def ws_event_bridge(event: Event):
    import asyncio
    print(f"[BRIDGE] Received event: {event.event_type}")
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast_event(event), loop)
    except Exception as e:
        print(f"[BRIDGE ERROR] {e}")

# Register the bridge globally
print("[SERVER] Registering WS Event Bridge...")
from oao.runtime.events import GlobalEventRegistry
for event_type in EventType:
    GlobalEventRegistry.register(event_type, ws_event_bridge)
print(f"[SERVER] Registered bridge for {len(EventType)} event types")

# Optional: Distributed scheduler (requires redis)
try:
    from oao.runtime.distributed_scheduler import DistributedScheduler
    DISTRIBUTED_ENABLED = True
except ImportError:
    DISTRIBUTED_ENABLED = False


app = FastAPI(title="OpenAgentOrchestrator API")

# -----------------------------------------------------
# CORS
# -----------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------
# Startup Hooks
# -----------------------------------------------------

@app.on_event("startup")
async def startup_event():
    """
    On server startup, attempt to recover crashed executions.
    """
    try:
        from oao.runtime.recovery import RecoveryManager
        import asyncio
        manager = RecoveryManager()
        # Launch recovery in background
        asyncio.create_task(manager.recover_executions())
    except Exception as e:
        print(f"[ERROR] Failed to init recovery manager: {e}")

# -----------------------------------------------------
# Request Schemas
# -----------------------------------------------------


class SingleAgentRequest(BaseModel):
    task: str
    framework: str = "langchain"
    max_steps: int = 10
    max_tokens: int = 4000


class MultiAgentRequest(BaseModel):
    task: str
    framework: str = "langchain"
    max_concurrency: int = 3
    agent_count: int = 2


class ReplayRequest(SingleAgentRequest):
    execution_id: str
    from_step: int


# -----------------------------------------------------
# Routes
# -----------------------------------------------------


@app.get("/")
def health_check():
    return {"status": "OAO Server Running"}


@app.get("/metrics")
def metrics_endpoint():
    """
    Expose Prometheus metrics.
    """
    # Update queue size if distributed
    if DISTRIBUTED_ENABLED:
        try:
            scheduler = DistributedScheduler()
            metrics.queue_size.set(scheduler.get_queue_length())
        except Exception:
            pass  # Ignore redis errors for metrics

    return Response(generate_latest(), media_type="text/plain")


@app.post("/run")
async def run_single_agent(request: SingleAgentRequest):

    policy = StrictPolicy(
        max_steps=request.max_steps,
        max_tokens=request.max_tokens,
    )

    orch = Orchestrator(policy=policy)
    
    # Pre-generate execution ID to save spec for recovery
    execution_id = str(uuid.uuid4())
    
    # Save execution spec
    from oao.runtime.persistence import RedisPersistenceAdapter
    try:
        persistence = RedisPersistenceAdapter()
        persistence.save_execution_spec(execution_id, request.dict())
    except Exception as e:
        print(f"[WARNING] Failed to save execution spec for recovery: {e}")

    agent = AgentFactory.create_agent(request.framework)

    report = await orch.run_async(
        agent=agent,
        task=request.task,
        framework=request.framework,
        execution_id=execution_id
    )

    return report.dict()


@app.post("/replay")
async def replay_execution(request: ReplayRequest):
    """
    Replay an execution from a specific step.
    """
    policy = StrictPolicy(
        max_steps=request.max_steps,
        max_tokens=request.max_tokens,
    )

    orch = Orchestrator(policy=policy)

    # Re-create agent based on request
    # Note: State is not rehydrated here, but inside run_async via persistence
    agent = AgentFactory.create_agent(request.framework)

    report = await orch.run_async(
        agent=agent,
        task=request.task,
        framework=request.framework,
        execution_id=request.execution_id,
        from_step=request.from_step
    )

    return report.dict()


@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for dashboard clients to receive real-time events.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, though we mostly broadcast
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/executions/{execution_id}/trace")
async def get_execution_trace(execution_id: str):
    """
    Fetch the complete event log for an execution.
    Used for re-visualizing historical executions.
    """
    from oao.runtime.event_store import RedisEventStore
    
    # Try Redis first, then fallback to internal memory if necessary
    try:
        store = RedisEventStore()
        events = store.get_events(execution_id)
        if not events:
            return {"execution_id": execution_id, "events": [], "message": "No events found in Redis"}
            
        return {
            "execution_id": execution_id,
            "events": [e.to_dict() for e in events]
        }
    except Exception as e:
        return {"error": str(e), "execution_id": execution_id}


@app.post("/run-multi")
async def run_multi_agent(request: MultiAgentRequest):

    agents = {
        f"agent_{i}": AgentFactory.create_agent(request.framework)
        for i in range(request.agent_count)
    }

    multi_orch = MultiAgentOrchestrator(
        max_concurrency=request.max_concurrency
    )

    results = await multi_orch.run_multi_async(
        agents=agents,
        task=request.task,
        framework=request.framework,
    )

    # Convert ExecutionReport objects to dicts for JSON serialization
    return {
        name: report.model_dump() if hasattr(report, 'model_dump') else report.dict()
        for name, report in results.items()
    }


@app.get("/demo/scenarios")
async def run_demo_scenarios_route():
    """
    Triggers 3 test scenarios directly on the server to populate the dashboard.
    """
    import asyncio
    from oao.runtime.orchestrator import Orchestrator
    from oao.policy.strict_policy import StrictPolicy

    class MockDashboardAgent:
        def __init__(self, name, steps=3, error_at=None):
            self.name = name
            self.steps = steps
            self.error_at = error_at
            self.current = 0

        async def ainvoke(self, task, **kwargs):
            self.current += 1
            await asyncio.sleep(0.5)
            if self.error_at == self.current:
                raise ValueError(f"Error in {self.name} at step {self.current}")
            return {"output": f"{self.name} step {self.current} done", "token_usage": 100}
        
        def invoke(self, task, **kwargs):
            self.current += 1
            if self.error_at == self.current:
                raise ValueError(f"Error in {self.name} at step {self.current}")
            return {"output": f"{self.name} step {self.current} done", "token_usage": 100}

    async def run_internal():
        from oao.runtime.persistence import InMemoryPersistenceAdapter
        from oao.runtime.event_store import InMemoryEventStore
        
        # Scenario 1: Success
        # Use in-memory adapters for demo to avoid Redis dependency
        persistence = InMemoryPersistenceAdapter()
        event_store = InMemoryEventStore()
        
        orch1 = Orchestrator(persistence=persistence, event_store=event_store)
        for et in EventType: orch1.event_bus.register(et, ws_event_bridge)
        
        await orch1.run_async(MockDashboardAgent("SuccessBot", steps=3), "Task A", framework="mock")
        
        await asyncio.sleep(1)
        
        # Scenario 2: Failure
        orch2 = Orchestrator(persistence=persistence, event_store=event_store)
        for et in EventType: orch2.event_bus.register(et, ws_event_bridge)
        
        try:
            await orch2.run_async(MockDashboardAgent("BuggyBot", steps=3, error_at=2), "Task B", framework="mock")
        except Exception: pass
        
        await asyncio.sleep(1)
        
        # Scenario 3: Policy Violation
        policy = StrictPolicy(max_steps=2)
        orch3 = Orchestrator(persistence=persistence, event_store=event_store, policy=policy)
        for et in EventType: orch3.event_bus.register(et, ws_event_bridge)
        
        try:
            await orch3.run_async(MockDashboardAgent("RunawayBot", steps=5), "Task C", framework="mock")
        except Exception: pass

    # Run in background to return immediately
    asyncio.create_task(run_internal())
    
    return {"message": "Demo scenarios started in background"}

# -----------------------------------------------------
# Distributed Endpoints (requires Redis)
# -----------------------------------------------------

if DISTRIBUTED_ENABLED:
    
    @app.post("/run-distributed")
    async def run_distributed(request: SingleAgentRequest):
        """
        Submit a job to the distributed queue.
        Workers will process the job asynchronously.
        """
        scheduler = DistributedScheduler()
        job_id = scheduler.submit_job(request.dict())
        
        return {
            "job_id": job_id,
            "status": "PENDING",
            "message": "Job submitted to distributed queue"
        }
    
    @app.get("/job/{job_id}")
    async def get_job_result(job_id: str, wait: Optional[int] = 0):
        """
        Get the result of a distributed job.
        
        Args:
            job_id: Unique job identifier
            wait: Optional timeout to wait for result (seconds)
        """
        scheduler = DistributedScheduler()
        
        try:
            status = scheduler.get_status(job_id)
            
            if status.value in ["SUCCESS", "FAILED"]:
                result = scheduler.fetch_result(job_id, timeout=0)
                if result:
                    return result
            
            # If waiting is requested and job is pending/running
            if wait > 0:
                result = scheduler.fetch_result(job_id, timeout=wait)
                if result:
                    # The following lines seem to be misplaced from a different context (e.g., a WebSocket event loop)
                    # and refer to an undefined variable 'message'.
                    # To make the code syntactically correct and avoid errors,
                    # I'm commenting out the problematic lines and adding a placeholder print.
                    # If the intention was to process 'result' as JSON, it should be done here.
                    # data = json.loads(message)
                    # while isinstance(data, str):
                    #     data = json.loads(data)
                    
                    # if not isinstance(data, dict):
                    #     print(f"Non-dict data: {type(data)} -> {data}")
                    #     continue # 'continue' is not valid outside a loop
                    
                    # event_type = data.get("type", "UNKNOWN")
                    print(f"Job {job_id} result received after waiting: {result}") # Placeholder print
                    return result # Assuming 'result' is already in a suitable format
            
            # Return status if no result yet
            return {
                "job_id": job_id,
                "status": status.value,
                "message": "Job is still processing"
            }
            
        except ValueError as e:
            return {
                "error": str(e),
                "job_id": job_id
            }
    
    @app.get("/queue/status")
    async def get_queue_status():
        """
        Get the status of the job queue.
        """
        scheduler = DistributedScheduler()
        queue_length = scheduler.get_queue_length()
        
        return {
            "queue_length": queue_length,
            "distributed_enabled": True
        }
else:
    @app.get("/distributed/status")
    async def distributed_disabled():
        return {
            "distributed_enabled": False,
            "message": "Install redis with: pip install open-agent-orchestrator[distributed]"
        }

@app.get("/test-event")
async def test_event_route():
    from oao.runtime.event_bus import EventBus
    from oao.runtime.events import Event, EventType
    eb = EventBus()
    eb.emit(Event(EventType.STATE_ENTER, {"payload": {"state": "TEST_MANUAL", "execution_id": "test-id"}, "event_type": EventType.STATE_ENTER}))
    return {"message": "Test event emitted manually"}
