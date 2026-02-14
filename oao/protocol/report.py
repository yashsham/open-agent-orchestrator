from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import uuid4


class ExecutionReport(BaseModel):
    execution_id: str
    agent_name: str
    status: str
    total_tokens: int
    total_steps: int
    tool_calls: int
    execution_time_seconds: float
    state_history: List[str]
    final_output: Optional[str]
    timestamp: datetime

    @staticmethod
    def create(
        agent_name: str,
        status: str,
        total_tokens: int,
        total_steps: int,
        tool_calls: int,
        execution_time_seconds: float,
        state_history: List[str],
        final_output: Optional[str],
    ):
        return ExecutionReport(
            execution_id=str(uuid4()),
            agent_name=agent_name,
            status=status,
            total_tokens=total_tokens,
            total_steps=total_steps,
            tool_calls=tool_calls,
            execution_time_seconds=execution_time_seconds,
            state_history=state_history,
            final_output=final_output,
            timestamp=datetime.utcnow(),
        )
