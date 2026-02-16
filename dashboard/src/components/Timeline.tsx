import type { OAOEvent } from '../types';

interface TimelineProps {
    events: OAOEvent[];
    executionId: string | null;
}

export function Timeline({ events, executionId }: TimelineProps) {
    if (!executionId) return null;

    const relevantEvents = events.filter(e => e.execution_id === executionId);
    const steps = relevantEvents.filter(e => e.step_number !== undefined);

    // Group by step number
    const stepMap: Record<number, { start?: string, end?: string, type?: string }> = {};
    steps.forEach(e => {
        const num = e.step_number!;
        if (!stepMap[num]) stepMap[num] = {};
        if (e.event_type.includes('START')) stepMap[num].start = e.timestamp;
        if (e.event_type.includes('COMPLET')) stepMap[num].end = e.timestamp;
        stepMap[num].type = e.event_type.replace('_STARTED', '').replace('_COMPLETED', '');
    });

    const stepNumbers = Object.keys(stepMap).map(Number).sort((a, b) => a - b);

    return (
        <div className="bg-slate-800 p-4 rounded-xl border border-slate-700">
            <h3 className="text-sm font-semibold text-slate-400 uppercase mb-4">Execution Timeline</h3>
            <div className="space-y-4">
                {stepNumbers.length === 0 && <p className="text-slate-500 text-xs text-center py-4">No steps recorded for this execution yet.</p>}
                {stepNumbers.map(num => {
                    const step = stepMap[num];
                    const duration = step.start && step.end ? (new Date(step.end).getTime() - new Date(step.start).getTime()) : null;

                    return (
                        <div key={num} className="flex items-center gap-4">
                            <span className="w-16 text-[10px] font-mono text-slate-500">STEP {num}</span>
                            <div className="flex-1 bg-slate-700/50 h-6 rounded-full overflow-hidden relative border border-slate-600">
                                {step.start && (
                                    <div
                                        className={`absolute inset-y-0 bg-blue-500/50 border-r border-blue-400 ${step.end ? '' : 'animate-pulse'}`}
                                        style={{ left: '0%', width: step.end ? '100%' : '50%' }}
                                    >
                                        <span className="absolute left-2 inset-y-0 flex items-center text-[9px] font-bold text-blue-200">
                                            {step.type} {duration ? `(${duration}ms)` : '...'}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
