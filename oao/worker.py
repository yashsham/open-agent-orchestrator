import asyncio
import uuid
import signal
import sys
import time
import threading
from typing import Optional

from oao.runtime.distributed_scheduler import DistributedScheduler, JobStatus
from oao.runtime.orchestrator import Orchestrator
from oao.policy.strict_policy import StrictPolicy

class WorkerNode:
    """
    Background worker that processes jobs from the distributed queue.
    Features:
    - Heartbeats
    - Graceful Shutdown
    - Crash Recovery (automatic via Scheduler)
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.scheduler = DistributedScheduler(redis_url)
        self.worker_id = str(uuid.uuid4())[:8]
        self.running = False
        self.heartbeat_thread = None
        self._shutdown_event = threading.Event()

    def start(self):
        """Start the worker node."""
        self.running = True
        print(f"[WORKER] Starting WorkerNode {self.worker_id}")
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        # Start heartbeat
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

        # Run job loop
        self._job_loop()

    def _heartbeat_loop(self):
        """Send heartbeats to Redis periodically."""
        while not self._shutdown_event.is_set():
            try:
                self.scheduler.register_worker(self.worker_id, ttl=5)
                time.sleep(2)
            except Exception as e:
                print(f"[WORKER] Heartbeat error: {e}")
                time.sleep(5)

    def _job_loop(self):
        """Main loop to fetch and process jobs."""
        
        # Run recovery once on startup to clean up any previous mess
        try:
            self.scheduler.recover_dead_workers()
        except Exception:
            pass

        while self.running:
            try:
                # Fetch job with timeout (blocking)
                job = self.scheduler.fetch_job(self.worker_id, timeout=2)
                
                if job:
                    self._process_job(job)
                else:
                    # No job, check dead workers periodically
                    # In a real system, this might be a separate "reaper" process
                    pass

            except Exception as e:
                print(f"[WORKER] Loop error: {e}")
                time.sleep(1)

        print(f"[WORKER] Stopped {self.worker_id}")

    def _process_job(self, job):
        """Execute the job using Orchestrator."""
        job_id = job.get("job_id")
        payload = job.get("payload", {})
        
        print(f"[WORKER] Processing Job {job_id}")
        
        try:
            # Parse payload
            task = payload.get("task")
            framework = payload.get("framework", "langchain")
            agent_config = payload.get("agent_config", {}) # Logic to recreate agent
            
            # Recreate Agent (Simplification: assuming dummy or serializable agent for now)
            # In production, payload would contain agent_class and init_params
            from oao.runtime.agent_factory import AgentFactory
            agent = AgentFactory.create_agent(framework) 
            
            # Execute
            policy = StrictPolicy(max_steps=10)
            orch = Orchestrator(policy=policy)
            
            # We use the sync run for simplicity in this thread, 
            # but ideally this should be async loop.
            # Using run() wrapper.
            report = orch.run(agent, task, framework)
            
            # Complete
            self.scheduler.complete_job(self.worker_id, job_id, report.dict())
            print(f"[WORKER] Job {job_id} Completed")
            
        except Exception as e:
            print(f"[WORKER] Job {job_id} Failed: {e}")
            self.scheduler.fail_job(self.worker_id, job_id, str(e))

    def _handle_signal(self, signum, frame):
        print("\n[WORKER] Shutting down...")
        self.running = False
        self._shutdown_event.set()

if __name__ == "__main__":
    worker = WorkerNode()
    worker.start()
