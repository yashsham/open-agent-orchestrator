from enum import Enum, auto
from typing import Dict, List


class AgentState(Enum):
    INIT = auto()
    PLAN = auto()
    EXECUTE = auto()
    REVIEW = auto()
    TERMINATE = auto()
    FAILED = auto()


class InvalidStateTransition(Exception):
    pass


class StateMachine:
    """
    Deterministic lifecycle controller for OAO agents.
    """

    def __init__(self):
        self.current_state: AgentState = AgentState.INIT
        self.history: List[AgentState] = [self.current_state]

        # Define valid transitions
        self._transitions: Dict[AgentState, List[AgentState]] = {
            AgentState.INIT: [AgentState.PLAN, AgentState.FAILED],
            AgentState.PLAN: [AgentState.EXECUTE, AgentState.FAILED],
            AgentState.EXECUTE: [AgentState.REVIEW, AgentState.FAILED],
            AgentState.REVIEW: [AgentState.TERMINATE, AgentState.FAILED],
            AgentState.TERMINATE: [],
            AgentState.FAILED: []
        }

    def transition(self, next_state: AgentState):
        """
        Move to the next state if allowed.
        """
        if next_state not in self._transitions[self.current_state]:
            raise InvalidStateTransition(
                f"Invalid transition from {self.current_state.name} "
                f"to {next_state.name}"
            )

        self.current_state = next_state
        self.history.append(next_state)

    def fail(self):
        """
        Move to FAILED state immediately.
        """
        self.current_state = AgentState.FAILED
        self.history.append(AgentState.FAILED)

    def is_terminal(self) -> bool:
        """
        Returns True if execution has reached a terminal state.
        """
        return self.current_state in (
            AgentState.TERMINATE,
            AgentState.FAILED,
        )

    def get_state(self) -> AgentState:
        return self.current_state

    def get_history(self) -> List[AgentState]:
        return self.history
