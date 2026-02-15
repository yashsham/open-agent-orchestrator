import redis
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class DistributedScheduler:
    """
    Redis-backed distributed scheduler for horizontal scaling.
    
    Enables job submission to a Redis queue, allowing multiple worker
    nodes to process orchestration tasks concurrently.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize the distributed scheduler.
        
        Args:
            redis_url: Redis connection URL
        """
        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis.ping()
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Redis at {redis_url}.\n"
                f"Error: {e}\n"
                f"Install Redis with:\n"
                f"    docker run -p 6379:6379 redis\n"
                f"Or install redis-py with:\n"
                f"    pip install open-agent-orchestrator[distributed]"
            )

    def submit_job(self, payload: Dict[str, Any]) -> str:
        """
        Submit a job to the distributed queue.
        
        Args:
            payload: Job payload containing task details
            
        Returns:
            job_id: Unique identifier for the job
        """
        job_id = str(uuid.uuid4())
        
        job_data = {
            "job_id": job_id,
            "payload": payload,
            "status": JobStatus.PENDING,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # Store job metadata
        self.redis.hset(f"oao_job:{job_id}", mapping={
            "data": json.dumps(job_data),
            "status": JobStatus.PENDING,
        })
        
        # Push to job queue
        self.redis.rpush("oao_jobs", json.dumps({
            "job_id": job_id,
            "payload": payload
        }))
        
        return job_id

    def fetch_result(self, job_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        Fetch the result of a job.
        
        Args:
            job_id: Unique job identifier
            timeout: Maximum time to wait for result (seconds)
            
        Returns:
            Result dictionary or None if not ready/timeout
        """
        # Check if result exists
        result_key = f"oao_result:{job_id}"
        result = self.redis.get(result_key)
        
        if result:
            return json.loads(result)
        
        # If timeout is specified, wait for result
        if timeout > 0:
            for _ in range(timeout):
                result = self.redis.get(result_key)
                if result:
                    return json.loads(result)
                # Wait 1 second before retry
                import time
                time.sleep(1)
        
        return None

    def get_status(self, job_id: str) -> JobStatus:
        """
        Get the current status of a job.
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            JobStatus enum value
        """
        job_key = f"oao_job:{job_id}"
        status = self.redis.hget(job_key, "status")
        
        if not status:
            raise ValueError(f"Job {job_id} not found")
        
        return JobStatus(status)

    def set_status(self, job_id: str, status: JobStatus):
        """
        Update the status of a job.
        
        Args:
            job_id: Unique job identifier
            status: New status
        """
        job_key = f"oao_job:{job_id}"
        self.redis.hset(job_key, "status", status.value)
        self.redis.hset(job_key, "updated_at", datetime.utcnow().isoformat())

    def store_result(self, job_id: str, result: Dict[str, Any]):
        """
        Store the result of a job execution.
        
        Args:
            job_id: Unique job identifier
            result: Result data to store
        """
        result_key = f"oao_result:{job_id}"
        self.redis.set(result_key, json.dumps(result))
        self.redis.expire(result_key, 3600)  # Expire after 1 hour
        
        # Update status
        status = JobStatus.SUCCESS if result.get("status") == "SUCCESS" else JobStatus.FAILED
        self.set_status(job_id, status)

    def get_queue_length(self) -> int:
        """Get the number of pending jobs in the queue."""
        return self.redis.llen("oao_jobs")

    def clear_queue(self):
        """Clear all jobs from the queue (for testing/maintenance)."""
        self.redis.delete("oao_jobs")
