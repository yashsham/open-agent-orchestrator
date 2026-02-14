from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import asyncio
from typing import Dict, Any, List

from oao.runtime.orchestrator import Orchestrator
from oao.runtime.multi_agent import MultiAgentOrchestrator
from oao.policy.strict_policy import StrictPolicy
from oao.protocol.report import ExecutionReport
from oao.api_models import RunRequest, RunResponse
from oao.adapters.langchain_adapter import LangChainAdapter # Ensure registration

# Dummy Agent for testing
class DummyAgent:
    def __init__(self, name="DummyAgent"):
        self.name = name

    def invoke(self, task: str):
        return {"output": f"{self.name} processed: {task}"}

app = FastAPI(title="Open Agent Orchestrator API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for execution state
# Format: { execution_id: {"status": "RUNNING" | "COMPLETED" | "FAILED", "report": ExecutionReport, "task": str} }
executions: Dict[str, Dict[str, Any]] = {}

class SimpleRunRequest(BaseModel):
    task: str

class MultiRunRequest(BaseModel):
    task: str
    agent_count: int = 3

@app.post("/run")
async def run_agent_blocking(request: SimpleRunRequest):
    """
    Blocking endpoint for single agent execution (for frontend convenience)
    """
    agent = DummyAgent()
    orch = Orchestrator(policy=StrictPolicy())
    
    # Run async and wait
    report = await orch.run_async(agent, request.task)
    
    return report

@app.post("/run-multi")
async def run_multi_blocking(request: MultiRunRequest):
    """
    Blocking endpoint for multi-agent execution
    """
    # Create N agents
    agents = {
        f"Agent-{i+1}": DummyAgent(f"Agent-{i+1}")
        for i in range(request.agent_count)
    }
    
    multi_orch = MultiAgentOrchestrator(max_concurrency=3)
    
    results = await multi_orch.run_multi_async(
        agents=agents,
        task=request.task
    )
    
    return results

async def run_agent_background(execution_id: str, agent_name: str, task: str):
    try:
        # In a real app, we'd lookup the agent by name from a registry
        agent = DummyAgent() 
        
        orch = Orchestrator(policy=StrictPolicy())
        
        # Update status to RUNNING
        executions[execution_id]["status"] = "RUNNING"
        
        report = await orch.run_async(agent, task)
        
        executions[execution_id]["status"] = report.status
        executions[execution_id]["report"] = report
        
    except Exception as e:
        executions[execution_id]["status"] = "FAILED"
        executions[execution_id]["error"] = str(e)

@app.post("/agent/run", response_model=RunResponse)
async def run_agent(request: RunRequest, background_tasks: BackgroundTasks):
    execution_id = str(uuid.uuid4())
    
    executions[execution_id] = {
        "status": "PENDING",
        "task": request.task,
        "agent": request.agent_name,
        "report": None
    }
    
    background_tasks.add_task(run_agent_background, execution_id, request.agent_name, request.task)
    
    return RunResponse(
        execution_id=execution_id,
        status="PENDING",
        message="Agent execution started in background"
    )

@app.get("/agent/status/{execution_id}")
async def get_status(execution_id: str):
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail="Execution ID not found")
    
    return {
        "execution_id": execution_id,
        "status": executions[execution_id]["status"]
    }

@app.get("/agent/report/{execution_id}")
async def get_report(execution_id: str):
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail="Execution ID not found")
        
    data = executions[execution_id]
    
    if data["status"] == "PENDING" or data["status"] == "RUNNING":
        return {"status": data["status"], "message": "Execution in progress"}
    
    if data["report"]:
        return data["report"]
        
    return {"status": data["status"], "error": data.get("error")}
