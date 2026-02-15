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

from typing import Dict, Optional

from oao.runtime.orchestrator import Orchestrator
from oao.runtime.multi_agent import MultiAgentOrchestrator
from oao.runtime.agent_factory import AgentFactory
from oao.policy.strict_policy import StrictPolicy
import oao.metrics as metrics
from prometheus_client import generate_latest
from fastapi import Response

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

    agent = AgentFactory.create_agent(request.framework)

    report = await orch.run_async(
        agent=agent,
        task=request.task,
        framework=request.framework,
    )

    return report.dict()


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
                    return result
            
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
