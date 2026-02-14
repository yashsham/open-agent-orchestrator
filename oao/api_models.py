from typing import Optional, Dict, Any
from pydantic import BaseModel

class RunRequest(BaseModel):
    agent_name: str
    task: str
    framework: str = "langchain"

class RunResponse(BaseModel):
    execution_id: str
    status: str
    message: str = "Agent execution started"
