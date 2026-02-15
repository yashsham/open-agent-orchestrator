import asyncio
import json
import time
from typing import Optional
import signal
import sys

try:
    import redis
except ImportError:
    raise ImportError(
        "Redis is not installed.\n"
        "Install with:\n"
        "    pip install open-agent-orchestrator[distributed]"
    )

from oao.runtime.orchestrator import Orchestrator
from oao.runtime.agent_factory import AgentFactory
from oao.policy.strict_policy import StrictPolicy


class WorkerNode:
    """
    Background worker that processes jobs from Redis queue.
    
    Workers poll the job queue, execute orchestration tasks,
    and store results back to Redis.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        worker_id: Optional[str] = None,
        poll_interval: float = 1.0
    ):
        """
        Initialize worker node.
        
        Args:
            redis_url: Redis connection URL
            worker_id: Unique worker identifier (auto-generated if None)
            poll_interval: Seconds to wait between queue polls
        """
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.worker_id = worker_id or f"worker-{int(time.time())}"
        self.poll_interval = poll_interval
        self.running = False
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown on SIGINT/SIGTERM."""
        print(f"\n[WORKER-{self.worker_id}] Shutting down gracefully...")
        self.running = False

    def start(self):
        """
        Start the worker in blocking mode.
        
        Continuously polls Redis queue and processes jobs.
        """
        print(f"[WORKER-{self.worker_id}] Starting...")
        self.running = True
        
        while self.running:
            try:
                # Blocking pop with timeout (BLPOP)
                result = self.redis.blpop("oao_jobs", timeout=int(self.poll_interval))
                
                if result:
                    _, job_json = result
                    job_data = json.loads(job_json)
                    self._process_job(job_data)
                    
            except redis.ConnectionError as e:
                print(f"[WORKER-{self.worker_id}] Redis connection error: {e}")
                time.sleep(self.poll_interval)
            except Exception as e:
                print(f"[WORKER-{self.worker_id}] Unexpected error: {e}")
                time.sleep(self.poll_interval)

        print(f"[WORKER-{self.worker_id}] Stopped")

    async def start_async(self):
        """
        Start the worker in async mode.
        
        Similar to start() but uses async/await.
        """
        print(f"[WORKER-{self.worker_id}] Starting (async)...")
        self.running = True
        
        while self.running:
            try:
                # Use sync blpop with asyncio.to_thread to avoid blocking event loop
                result = await asyncio.to_thread(
                    self.redis.blpop, "oao_jobs", int(self.poll_interval)
                )
                
                if result:
                    _, job_json = result
                    job_data = json.loads(job_json)
                    await self._process_job_async(job_data)
                    
            except redis.ConnectionError as e:
                print(f"[WORKER-{self.worker_id}] Redis connection error: {e}")
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                print(f"[WORKER-{self.worker_id}] Unexpected error: {e}")
                await asyncio.sleep(self.poll_interval)

        print(f"[WORKER-{self.worker_id}] Stopped")

    def _process_job(self, job_data: dict):
        """Process a job synchronously."""
        job_id = job_data["job_id"]
        payload = job_data["payload"]
        
        print(f"[WORKER-{self.worker_id}] Processing job {job_id}")
        
        # Update status to RUNNING
        self.redis.hset(f"oao_job:{job_id}", "status", "RUNNING")
        
        try:
            # Extract job parameters
            task = payload.get("task", "")
            framework = payload.get("framework", "langchain")
            max_steps = payload.get("max_steps", 10)
            max_tokens = payload.get("max_tokens", 10000)
            
            # Create agent and orchestrator
            agent = AgentFactory.create_agent(framework)
            policy = StrictPolicy(max_steps=max_steps, max_tokens=max_tokens)
            orch = Orchestrator(policy=policy)
            
            # Execute task
            report = orch.run(agent=agent, task=task, framework=framework)
            
            # Store result
            result = report.dict() if hasattr(report, 'dict') else report.model_dump()
            self.redis.set(f"oao_result:{job_id}", json.dumps(result))
            self.redis.expire(f"oao_result:{job_id}", 3600)  # 1 hour TTL
            
            # Update status
            status = "SUCCESS" if result.get("status") == "SUCCESS" else "FAILED"
            self.redis.hset(f"oao_job:{job_id}", "status", status)
            
            print(f"[WORKER-{self.worker_id}] Job {job_id} completed: {status}")
            
        except Exception as e:
            # Store error result
            error_result = {
                "status": "FAILED",
                "error": str(e),
                "job_id": job_id
            }
            self.redis.set(f"oao_result:{job_id}", json.dumps(error_result))
            self.redis.expire(f"oao_result:{job_id}", 3600)
            self.redis.hset(f"oao_job:{job_id}", "status", "FAILED")
            
            print(f"[WORKER-{self.worker_id}] Job {job_id} failed: {e}")

    async def _process_job_async(self, job_data: dict):
        """Process a job asynchronously."""
        job_id = job_data["job_id"]
        payload = job_data["payload"]
        
        print(f"[WORKER-{self.worker_id}] Processing job {job_id} (async)")
        
        # Update status to RUNNING
        await asyncio.to_thread(self.redis.hset, f"oao_job:{job_id}", "status", "RUNNING")
        
        try:
            # Extract job parameters
            task = payload.get("task", "")
            framework = payload.get("framework", "langchain")
            max_steps = payload.get("max_steps", 10)
            max_tokens = payload.get("max_tokens", 10000)
            
            # Create agent and orchestrator
            agent = AgentFactory.create_agent(framework)
            policy = StrictPolicy(max_steps=max_steps, max_tokens=max_tokens)
            orch = Orchestrator(policy=policy)
            
            # Execute task asynchronously
            report = await orch.run_async(agent=agent, task=task, framework=framework)
            
            # Store result
            result = report.dict() if hasattr(report, 'dict') else report.model_dump()
            await asyncio.to_thread(self.redis.set, f"oao_result:{job_id}", json.dumps(result))
            await asyncio.to_thread(self.redis.expire, f"oao_result:{job_id}", 3600)
            
            # Update status
            status = "SUCCESS" if result.get("status") == "SUCCESS" else "FAILED"
            await asyncio.to_thread(self.redis.hset, f"oao_job:{job_id}", "status", status)
            
            print(f"[WORKER-{self.worker_id}] Job {job_id} completed: {status}")
            
        except Exception as e:
            # Store error result
            error_result = {
                "status": "FAILED",
                "error": str(e),
                "job_id": job_id
            }
            await asyncio.to_thread(self.redis.set, f"oao_result:{job_id}", json.dumps(error_result))
            await asyncio.to_thread(self.redis.expire, f"oao_result:{job_id}", 3600)
            await asyncio.to_thread(self.redis.hset, f"oao_job:{job_id}", "status", "FAILED")
            
            print(f"[WORKER-{self.worker_id}] Job {job_id} failed (async): {e}")
