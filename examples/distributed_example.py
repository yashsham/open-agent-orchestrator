"""
Example: Distributed Job Execution with Redis

This example demonstrates how to use the distributed scheduler
to submit jobs to a Redis queue for processing by worker nodes.

Prerequisites:
1. Install Redis: docker run -p 6379:6379 redis
2. Install OAO with distributed support: pip install "open-agent-orchestrator[distributed]"
3. Start worker: python -m oao.worker

Then run this script to submit a job.
"""

import time
from oao.runtime.distributed_scheduler import DistributedScheduler


def main():
    # Initialize scheduler
    scheduler = DistributedScheduler(redis_url="redis://localhost:6379/0")
    
    # Submit a job
    job_payload = {
        "task": "Explain the benefits of distributed systems",
        "framework": "langchain",
        "max_steps": 5,
        "max_tokens": 2000
    }
    
    print("Submitting job to distributed queue...")
    job_id = scheduler.submit_job(job_payload)
    print(f"Job submitted: {job_id}")
    
    # Poll for result
    print("\nWaiting for result...")
    print("(Make sure a worker is running: python -m oao.worker)\n")
    
    max_wait = 60  # Wait up to 60 seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        status = scheduler.get_status(job_id)
        print(f"Job status: {status.value}")
        
        if status.value in ["SUCCESS", "FAILED"]:
            result = scheduler.fetch_result(job_id, timeout=0)
            if result:
                print("\n" + "="*50)
                print("JOB RESULT:")
                print("="*50)
                print(f"Status: {result.get('status')}")
                print(f"Final Output: {result.get('final_output')}")
                print(f"Total Steps: {result.get('total_steps')}")
                print("="*50)
                break
        
        time.sleep(2)
    else:
        print(f"\nTimeout: Job did not complete within {max_wait} seconds")
        print("Check that worker is running and processing jobs")


if __name__ == "__main__":
    main()
