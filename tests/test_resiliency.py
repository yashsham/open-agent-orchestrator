import unittest
import time
import json
import fakeredis
from unittest import mock
from datetime import datetime, timedelta
from oao.runtime.distributed_scheduler import DistributedScheduler, JobStatus

class TestSchedulerResiliency(unittest.TestCase):
    def setUp(self):
        # Use fakeredis for isolation
        self.redis = fakeredis.FakeRedis(decode_responses=True)
        
        # Patch redis.from_url to return our fake redis
        # We need to do this because DistributedScheduler connects in __init__
        with unittest.mock.patch('redis.from_url', return_value=self.redis):
            self.scheduler = DistributedScheduler()

    def test_retry_logic(self):
        print("\nTesting Retry Logic...")
        # Submit job with 2 retries
        job_id = self.scheduler.submit_job({"task": "fail_me"}, retries=2)
        worker_id = "worker_retry_test"
        
        # 1st Attempt: Fetch & Fail
        job = self.scheduler.fetch_job(worker_id)
        self.assertIsNotNone(job)
        self.scheduler.fail_job(worker_id, job_id, "Simulated Failure 1")
        
        # Verify it's back in queue
        self.assertEqual(self.scheduler.get_queue_length(), 1)
        job_status = self.scheduler.get_status(job_id)
        self.assertEqual(job_status, JobStatus.PENDING)
        
        # Verify retries decremented
        job_data = json.loads(self.redis.hget(f"oao_job:{job_id}", "data"))
        self.assertEqual(job_data["retries_left"], 1)
        print("✅ First retry requeued correctly")

        # 2nd Attempt: Fetch & Fail
        job = self.scheduler.fetch_job(worker_id)
        self.scheduler.fail_job(worker_id, job_id, "Simulated Failure 2")
        
        # Verify it's back in queue
        self.assertEqual(self.scheduler.get_queue_length(), 1)
        job_data = json.loads(self.redis.hget(f"oao_job:{job_id}", "data"))
        self.assertEqual(job_data["retries_left"], 0)
        print("✅ Second retry requeued correctly")

        # 3rd Attempt: Fetch & Fail Permanently
        job = self.scheduler.fetch_job(worker_id)
        self.scheduler.fail_job(worker_id, job_id, "Simulated Failure 3")
        
        # Verify FAILED status and NOT in queue
        self.assertEqual(self.scheduler.get_queue_length(), 0)
        job_status = self.scheduler.get_status(job_id)
        self.assertEqual(job_status, JobStatus.FAILED)
        print("✅ Permanent failure correctly handled")

    def test_crash_recovery(self):
        print("\nTesting Crash Recovery...")
        # Submit job
        job_id = self.scheduler.submit_job({"task": "crash_me"})
        dead_worker = "dead_worker_1"
        live_worker = "live_worker_1"
        
        # 1. Dead worker picks up job
        self.scheduler.register_worker(dead_worker, ttl=1) # Short TTL
        job = self.scheduler.fetch_job(dead_worker)
        self.assertIsNotNone(job)
        
        # Verify job is in processing queue of dead worker
        processing_queue = f"oao_processing:{dead_worker}"
        self.assertEqual(self.redis.llen(processing_queue), 1)
        self.assertEqual(self.scheduler.get_queue_length(), 0)
        
        # 2. Simulate Crash (Wait for TTL to expire)
        print("⏳ Waiting for worker heartbeat to expire...")
        time.sleep(1.2)
        
        # 3. Verify worker detection
        dead_workers = self.scheduler.get_dead_workers()
        self.assertIn(dead_worker, dead_workers)
        print(f"✅ Detected dead worker: {dead_worker}")
        
        # 4. Run Recovery
        self.scheduler.recover_dead_workers()
        
        # 5. Verify job is back in main queue
        self.assertEqual(self.scheduler.get_queue_length(), 1)
        self.assertEqual(self.redis.llen(processing_queue), 0)
        print("✅ Job recovered to main queue")
        
        # 6. Live worker picks it up
        self.scheduler.register_worker(live_worker, ttl=60)
        recovered_job = self.scheduler.fetch_job(live_worker)
        self.assertEqual(recovered_job["job_id"], job_id)
        print("✅ Live worker picked up recovered job")

if __name__ == "__main__":
    unittest.main()
