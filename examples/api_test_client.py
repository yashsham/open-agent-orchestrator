from fastapi.testclient import TestClient
from oao.server import app
import time

client = TestClient(app)

def test_api_workflow():
    print("Sending run request...")
    response = client.post("/agent/run", json={"agent_name": "TestAgent", "task": "Explain API"})
    assert response.status_code == 200
    data = response.json()
    execution_id = data["execution_id"]
    print(f"Execution started: {execution_id}")

    # Poll for completion
    while True:
        status_res = client.get(f"/agent/status/{execution_id}")
        assert status_res.status_code == 200
        status = status_res.json()["status"]
        print(f"Status: {status}")
        
        if status in ["COMPLETED", "FAILED", "SUCCESS"]:
            break
        
        time.sleep(0.5)

    # Get Report
    report_res = client.get(f"/agent/report/{execution_id}")
    assert report_res.status_code == 200
    report = report_res.json()
    
    print("\nExecution Report:")
    print(report)

if __name__ == "__main__":
    test_api_workflow()
