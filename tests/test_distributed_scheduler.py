import pytest
import time
from unittest.mock import Mock, patch
from oao.runtime.distributed_scheduler import DistributedScheduler, JobStatus


# Skip tests if Redis not available
pytest.importorskip("redis")


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch('redis.from_url') as mock:
        redis_mock = Mock()
        redis_mock.ping.return_value = True
        mock.return_value = redis_mock
        yield redis_mock


def test_scheduler_initialization(mock_redis):
    """Test scheduler initializes with Redis connection."""
    scheduler = DistributedScheduler()
    assert scheduler.redis == mock_redis
    mock_redis.ping.assert_called_once()


def test_submit_job(mock_redis):
    """Test job submission creates job in Redis."""
    scheduler = DistributedScheduler()
    
    payload = {"task": "test task", "framework": "langchain"}
    job_id = scheduler.submit_job(payload)
    
    # Verify job_id is UUID
    assert len(job_id) == 36  # UUID string length
    
    # Verify Redis calls
    assert mock_redis.hset.called
    assert mock_redis.rpush.called


def test_get_status(mock_redis):
    """Test status retrieval for a job."""
    mock_redis.hget.return_value = "PENDING"
    
    scheduler = DistributedScheduler()
    status = scheduler.get_status("test-job-id")
    
    assert status == JobStatus.PENDING
    mock_redis.hget.assert_called_with("oao_job:test-job-id", "status")


def test_get_status_not_found(mock_redis):
    """Test status retrieval for non-existent job."""
    mock_redis.hget.return_value = None
    
    scheduler = DistributedScheduler()
    
    with pytest.raises(ValueError, match="Job .* not found"):
        scheduler.get_status("invalid-job-id")


def test_fetch_result(mock_redis):
    """Test result fetching."""
    result_data = {"status": "SUCCESS", "output": "test output"}
    mock_redis.get.return_value = '{"status": "SUCCESS", "output": "test output"}'
    
    scheduler = DistributedScheduler()
    result = scheduler.fetch_result("test-job-id", timeout=0)
    
    assert result["status"] == "SUCCESS"
    assert result["output"] == "test output"


def test_fetch_result_not_ready(mock_redis):
    """Test result fetching when result not ready."""
    mock_redis.get.return_value = None
    
    scheduler = DistributedScheduler()
    result = scheduler.fetch_result("test-job-id", timeout=0)
    
    assert result is None


def test_store_result(mock_redis):
    """Test storing job result."""
    scheduler = DistributedScheduler()
    
    result = {"status": "SUCCESS", "output": "done"}
    scheduler.store_result("test-job-id", result)
    
    # Verify Redis calls
    assert mock_redis.set.called
    assert mock_redis.expire.called
    mock_redis.hset.assert_called_with("oao_job:test-job-id", "status", "SUCCESS")


def test_get_queue_length(mock_redis):
    """Test queue length retrieval."""
    mock_redis.llen.return_value = 5
    
    scheduler = DistributedScheduler()
    length = scheduler.get_queue_length()
    
    assert length == 5
    mock_redis.llen.assert_called_with("oao_jobs")


def test_clear_queue(mock_redis):
    """Test queue clearing."""
    scheduler = DistributedScheduler()
    scheduler.clear_queue()
    
    mock_redis.delete.assert_called_with("oao_jobs")
