export type EventType =
    | 'EXECUTION_STARTED'
    | 'EXECUTION_COMPLETED'
    | 'EXECUTION_FAILED'
    | 'STEP_STARTED'
    | 'STEP_COMPLETED'
    | 'TOOL_CALL_STARTED'
    | 'TOOL_CALL_COMPLETED'
    | 'STATE_ENTER'
    | 'POLICY_VIOLATION'
    | 'RETRY_ATTEMPTED';

export interface OAOEvent {
    event_id: string;
    event_type: EventType;
    timestamp: string;
    execution_id: string;
    step_number?: number;
    data: any;
}

export interface ExecutionSummary {
    execution_id: string;
    status: string;
    start_time: string;
    end_time?: string;
    step_count: number;
    token_usage: number;
}
