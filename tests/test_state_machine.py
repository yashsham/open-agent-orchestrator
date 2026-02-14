from oao.runtime.state_machine import StateMachine, AgentState

sm = StateMachine()

print(sm.get_state())

sm.transition(AgentState.PLAN)
sm.transition(AgentState.EXECUTE)
sm.transition(AgentState.REVIEW)
sm.transition(AgentState.TERMINATE)

print(sm.get_history())
