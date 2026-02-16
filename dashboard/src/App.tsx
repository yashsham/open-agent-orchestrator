import { useState, useEffect, useRef } from 'react';
import type { OAOEvent } from './types';
import { Timeline } from './components/Timeline';

function App() {
  const [events, setEvents] = useState<OAOEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [selectedExecution, setSelectedExecution] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Connect to OAO WebSocket
    // In production this would be configurable or relative
    const socket = new WebSocket('ws://localhost:8000/ws/events');

    socket.onopen = () => {
      setConnected(true);
      console.log('Connected to OAO Dashboard WS');
    };

    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type && msg.data) {
        setEvents(prev => [msg.data, ...prev].slice(0, 100));
        if (!selectedExecution) {
          setSelectedExecution(msg.data.execution_id);
        }
      }
    };

    socket.onclose = () => {
      setConnected(false);
      console.log('Disconnected from OAO Dashboard WS');
    };

    ws.current = socket;

    return () => {
      socket.close();
    };
  }, []);

  const executionIds = Array.from(new Set(events.map(e => e.execution_id)));

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6">
      <header className="flex justify-between items-center mb-8 border-b border-slate-700 pb-4">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
            OAO Observability
          </h1>
          <p className="text-slate-400">Deterministic AI Execution Runtime Dashboard</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.6)]' : 'bg-red-500'}`}></div>
          <span className="font-mono text-sm">{connected ? 'CONNECTED (v1.1.0)' : 'DISCONNECTED'}</span>
        </div>
      </header>

      <main className="grid grid-cols-12 gap-6">
        {/* Left Sidebar: Recent Executions */}
        <aside className="col-span-3 bg-slate-800 rounded-xl p-4 border border-slate-700 h-[calc(100vh-200px)] overflow-y-auto">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Recent Executions</h2>
          <div className="space-y-2">
            {executionIds.length === 0 && <p className="text-slate-500 text-sm">Waiting for events...</p>}
            {executionIds.map(id => (
              <button
                key={id}
                onClick={() => setSelectedExecution(id)}
                className={`w-full text-left p-3 rounded-lg text-xs font-mono break-all transition-all ${selectedExecution === id ? 'bg-purple-600/20 border border-purple-500 text-purple-300' : 'hover:bg-slate-700/50 border border-transparent'
                  }`}
              >
                {id}
              </button>
            ))}
          </div>
        </aside>

        {/* Center: Timeline & Events */}
        <section className="col-span-9 space-y-6">
          {/* Stats Bar */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-slate-800 p-4 rounded-xl border border-slate-700">
              <p className="text-slate-400 text-xs uppercase font-bold">Total Events</p>
              <p className="text-2xl font-bold">{events.length}</p>
            </div>
            <div className="bg-slate-800 p-4 rounded-xl border border-slate-700">
              <p className="text-slate-400 text-xs uppercase font-bold">Active ID</p>
              <p className="text-sm font-mono truncate">{selectedExecution || 'None'}</p>
            </div>
            <div className="bg-slate-800 p-4 rounded-xl border border-slate-700">
              <p className="text-slate-400 text-xs uppercase font-bold">Runtime</p>
              <p className="text-sm">Python / DAER</p>
            </div>
            <div className="bg-slate-800 p-4 rounded-xl border border-slate-700">
              <p className="text-slate-400 text-xs uppercase font-bold">Status</p>
              <p className="text-sm text-green-400 font-bold uppercase">Healthy</p>
            </div>
          </div>

          {/* Timeline Visualization */}
          <Timeline events={events} executionId={selectedExecution} />

          {/* Governance Watch */}
          <div className="bg-slate-800 p-4 rounded-xl border border-slate-700">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-sm font-semibold text-slate-400 uppercase">Governance Watch</h3>
              <span className="text-[10px] bg-purple-900/40 text-purple-300 px-2 py-0.5 rounded border border-purple-500/30">ENFORCING</span>
            </div>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span>Token Consumption</span>
                  <span className="font-mono text-purple-400">
                    {events.filter(e => e.execution_id === selectedExecution)
                      .reduce((acc, e) => acc + (e.data?.token_usage || 0), 0)} / 4000
                  </span>
                </div>
                <div className="w-full bg-slate-700 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-purple-500 h-full transition-all duration-500"
                    style={{ width: `${Math.min(100, (events.filter(e => e.execution_id === selectedExecution).reduce((acc, e) => acc + (e.data?.token_usage || 0), 0) / 4000) * 100)}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>

          {/* Event Log */}
          <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden flex flex-col h-[calc(100vh-320px)]">
            <div className="p-4 border-b border-slate-700 bg-slate-800/50 flex justify-between items-center">
              <h2 className="font-semibold text-slate-200">Execution Live Feed</h2>
              <button
                onClick={() => setEvents([])}
                className="text-xs text-slate-400 hover:text-slate-200 underline"
              >
                Clear Log
              </button>
            </div>
            <div className="overflow-y-auto p-2 font-mono text-xs">
              {events
                .filter(e => !selectedExecution || e.execution_id === selectedExecution)
                .map((event, i) => (
                  <div key={event.event_id || i} className="p-2 mb-1 rounded hover:bg-slate-700/30 flex gap-4 animate-in fade-in slide-in-from-left-2 duration-300">
                    <span className="text-slate-500 shrink-0">{new Date(event.timestamp).toLocaleTimeString()}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase shrink-0 h-fit ${event.event_type.includes('START') ? 'bg-blue-900/40 text-blue-300' :
                      event.event_type.includes('COMPLET') ? 'bg-green-900/40 text-green-300' :
                        event.event_type.includes('VIOLATION') || event.event_type.includes('FAIL') ? 'bg-red-900/40 text-red-300' :
                          'bg-slate-700 text-slate-300'
                      }`}>
                      {event.event_type}
                    </span>
                    <div className="flex-1">
                      <p className="text-slate-200">{JSON.stringify(event.data || {})}</p>
                    </div>
                  </div>
                ))}
              {events.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 py-20">
                  <div className="w-12 h-12 border-2 border-slate-700 border-t-purple-500 rounded-full animate-spin mb-4"></div>
                  <p>Awaiting events from Orchestrator...</p>
                </div>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
