import { useState } from "react";
import RunAgent from "./components/RunAgent";
import MultiAgent from "./components/MultiAgent";

function App() {
  return (
    <div style={{ padding: 30 }}>
      <h1>🔥 OpenAgentOrchestrator Dashboard</h1>
      <RunAgent />
      <hr />
      <MultiAgent />
    </div>
  );
}

export default App;
