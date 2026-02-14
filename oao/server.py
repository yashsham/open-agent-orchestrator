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

from typing import Dict

from oao.runtime.orchestrator import Orchestrator
from oao.runtime.multi_agent import MultiAgentOrchestrator
from oao.runtime.agent_factory import AgentFactory
from oao.policy.strict_policy import StrictPolicy


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
