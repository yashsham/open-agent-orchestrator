from enum import Enum, auto
from typing import Dict, List
import time


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
    
    Enforces valid state transitions and maintains full history.
    """

    def __init__(self):
        self.current_state: AgentState = AgentState.INIT
        self.history: List[AgentState] = [self.current_state]
        self.state_entry_times: Dict[AgentState, float] = {}
        self.state_entry_times[self.current_state] = time.time()

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
        
        Raises InvalidStateTransition if transition is not valid.
        """
        if next_state not in self._transitions[self.current_state]:
            raise InvalidStateTransition(
                f"Invalid transition from {self.current_state.name} "
                f"to {next_state.name}"
            )

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"State transition: {self.current_state.name} -> {next_state.name}")
        
        self.current_state = next_state
        self.history.append(next_state)
        self.state_entry_times[next_state] = time.time()

    def set_state(self, state: AgentState):
        """
        Force set the current state. Used for replay/restoration.
        
        Note: Even forced states are added to history to maintain integrity.
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Force setting state to {state.name} (bypass validation)")
        
        self.current_state = state
        # Always append to history, never bypass
        if not self.history or self.history[-1] != state:
            self.history.append(state)
            self.state_entry_times[state] = time.time()

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
    
    def get_current_state_duration(self) -> float:
        """
        Get the duration (in seconds) the state machine has been in the current state.
        """
        import time as time_module
        if self.current_state in self.state_entry_times:
            return time_module.time() - self.state_entry_times[self.current_state]
        return 0.0
