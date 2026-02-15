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

    def submit_job(self, payload: Dict[str, Any], retries: int = 3) -> str:
        """
        Submit a job to the distributed queue.
        
        Args:
            payload: Job payload containing task details
            retries: Number of retries allowed
            
        Returns:
            job_id: Unique identifier for the job
        """
        job_id = str(uuid.uuid4())
        
        job_data = {
            "job_id": job_id,
            "payload": payload,
            "status": JobStatus.PENDING,
            "retries_left": retries,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # Store job metadata
        self.redis.hset(f"oao_job:{job_id}", mapping={
            "data": json.dumps(job_data),
            "status": JobStatus.PENDING,
        })
        
        # Push to job queue
        self.redis.rpush("oao_jobs", json.dumps(job_data))
        
        return job_id

    def fetch_job(self, worker_id: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Reliably fetch a job from the queue using RPOPLPUSH pattern.
        Moves job from 'oao_jobs' to 'oao_processing:<worker_id>'.
        
        Args:
            worker_id: ID of the worker fetching the job
            timeout: Blocking timeout in seconds
            
        Returns:
            Job dictionary or None
        """
        # Reliable queue pop: moves from main queue to worker's processing list
        # We use brpoplpush to block until a job is available
        raw_job = self.redis.brpoplpush(
            "oao_jobs",
            f"oao_processing:{worker_id}",
            timeout=timeout
        )
        
        if raw_job:
            job = json.loads(raw_job)
            self.set_status(job["job_id"], JobStatus.RUNNING)
            return job
            
        return None

    def complete_job(self, worker_id: str, job_id: str, result: Dict[str, Any]):
        """
        Mark a job as complete and remove from processing queue.
        """
        # Remove from processing queue
        # LREM removes elements matching value. We need the original job payload...
        # Since we might not have the exact payload string easily, 
        # a better pattern for RPOPLPUSH is often to just have a generic 'processing' queue
        # but for per-worker isolation we used 'oao_processing:<worker_id>'.
        # To reliably remove, we should probably fetch the exact raw string first or just LPOP
        # since we assume head of list is the one we are processing if strict FIFO.
        # But for safety, let's try to remove by job_id match if we can, or just LPOP 
        # if the worker processes one by one.
        
        # Simpler approach: LPOP from processing queue. 
        # Assumption: Worker processes 1 job at a time per thread/queue.
        self.redis.lpop(f"oao_processing:{worker_id}")
        
        self.store_result(job_id, result)

    def fail_job(self, worker_id: str, job_id: str, error: str):
        """
        Handle job failure. Retry if retries left, else fail.
        """
        # Get current job data
        job_key = f"oao_job:{job_id}"
        data_str = self.redis.hget(job_key, "data")
        
        if data_str:
            job_data = json.loads(data_str)
            retries = job_data.get("retries_left", 0)
            
            # Remove from processing queue
            self.redis.lpop(f"oao_processing:{worker_id}")
            
            if retries > 0:
                # Decrement and requeue
                job_data["retries_left"] = retries - 1
                job_data["status"] = JobStatus.PENDING
                job_data["updated_at"] = datetime.utcnow().isoformat()
                
                # Update metadata
                self.redis.hset(job_key, "data", json.dumps(job_data))
                self.set_status(job_id, JobStatus.PENDING)
                
                # Push back to main queue
                self.redis.rpush("oao_jobs", json.dumps(job_data))
                print(f"[SCHEDULER] Job {job_id} failed. Retrying ({retries-1} left).")
            else:
                # Fail permanently
                print(f"[SCHEDULER] Job {job_id} failed permanently. Error: {error}")
                self.store_result(job_id, {"status": "FAILED", "error": error})

    # =====================================================
    # Worker Management & Recovery
    # =====================================================

    def register_worker(self, worker_id: str, ttl: int = 10):
        """Register a worker and update heartbeat."""
        key = f"oao_worker:{worker_id}"
        self.redis.set(key, "alive")
        self.redis.expire(key, ttl)

    def get_dead_workers(self) -> list:
        """Find workers that have processing queues but no heartbeat."""
        dead_workers = []
        
        # Scan for processing queues
        for key in self.redis.scan_iter("oao_processing:*"):
            worker_id = key.split(":")[1]
            # Check if heartbeat exists
            if not self.redis.exists(f"oao_worker:{worker_id}"):
                dead_workers.append(worker_id)
                
        return dead_workers

    def recover_dead_workers(self):
        """
        Requeue jobs from dead workers.
        """
        dead_workers = self.get_dead_workers()
        
        for worker_id in dead_workers:
            print(f"[RECOVERY] Recovering dead worker: {worker_id}")
            
            # Move all jobs from processing queue back to main queue
            while True:
                # RPOPLPUSH from processing back to main jobs
                # This puts it at the HEAD of jobs queue? Or TAIL?
                # RPOPLPUSH: Tail of source -> Head of dest.
                # So it becomes next to process. This is good (priority).
                job = self.redis.rpoplpush(f"oao_processing:{worker_id}", "oao_jobs")
                
                if not job:
                    break
                
                import oao.metrics as metrics
                if hasattr(metrics, 'requeued_jobs_counter'):
                    metrics.requeued_jobs_counter.inc()
                    
                print(f"[RECOVERY] Requeued job from {worker_id}")
                
            # Cleanup
            self.redis.delete(f"oao_processing:{worker_id}")


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
