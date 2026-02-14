import { useState } from "react";
import axios from "axios";
import ReportCard from "./ReportCard";

function RunAgent() {
    const [task, setTask] = useState("");
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(false);

    const runAgent = async () => {
        setLoading(true);
        try {
            const response = await axios.post(
                "http://127.0.0.1:8000/run",
                {
                    task: task,
                }
            );
            setReport(response.data);
        } catch (e) {
            console.error(e);
            setReport({ status: "ERROR", error: e.message || String(e) });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <h2>Single Agent</h2>
            <input
                type="text"
                placeholder="Enter task"
                value={task}
                onChange={(e) => setTask(e.target.value)}
            />
            <button onClick={runAgent} disabled={loading}>{loading ? "Running..." : "Run"}</button>

            {report && <ReportCard report={report} />}
        </div>
    );
}

export default RunAgent;
