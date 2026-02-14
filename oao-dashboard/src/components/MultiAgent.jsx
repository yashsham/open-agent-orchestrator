import { useState } from "react";
import axios from "axios";

function MultiAgent() {
    const [task, setTask] = useState("");
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);

    const runMulti = async () => {
        setLoading(true);
        try {
            const response = await axios.post(
                "http://127.0.0.1:8000/run-multi",
                {
                    task: task,
                    agent_count: 3,
                }
            );
            setResults(response.data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <h2>Multi-Agent</h2>
            <input
                type="text"
                placeholder="Enter task"
                value={task}
                onChange={(e) => setTask(e.target.value)}
            />
            <button onClick={runMulti} disabled={loading}>{loading ? "Running..." : "Run Multi"}</button>

            {results &&
                Object.keys(results).map((key) => (
                    <div key={key}>
                        <h4>{key}</h4>
                        <pre>{JSON.stringify(results[key], null, 2)}</pre>
                    </div>
                ))}
        </div>
    );
}

export default MultiAgent;
