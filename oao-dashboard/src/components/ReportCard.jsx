function ReportCard({ report }) {
    return (
        <div style={{ marginTop: 20, padding: 10, border: "1px solid gray" }}>
            <h3>Status: {report.status}</h3>
            <p>Agent: {report.agent_name}</p>
            <p>Steps: {report.total_steps}</p>
            <p>Tokens: {report.total_tokens}</p>
            <p>Execution Time: {report.execution_time_seconds.toFixed(2)}s</p>
            <pre>{report.final_output}</pre>
        </div>
    );
}

export default ReportCard;
