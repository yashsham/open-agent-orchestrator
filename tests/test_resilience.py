import unittest
from unittest.mock import MagicMock, patch, call, AsyncMock
import time
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oao.runtime.resilience import RetryConfig, BackoffStrategy, calculate_delay, should_retry, execute_with_retry, execute_with_retry_async

class TestResilience(unittest.TestCase):

    def test_calculate_delay_exponential(self):
        config = RetryConfig(
            initial_delay=1.0,
            backoff_factor=2.0,
            strategy=BackoffStrategy.EXPONENTIAL
        )
        self.assertEqual(calculate_delay(1, config), 1.0)
        self.assertEqual(calculate_delay(2, config), 2.0)
        self.assertEqual(calculate_delay(3, config), 4.0)

    def test_calculate_delay_linear(self):
        config = RetryConfig(
            initial_delay=1.0,
            strategy=BackoffStrategy.LINEAR
        )
        self.assertEqual(calculate_delay(1, config), 1.0)
        self.assertEqual(calculate_delay(2, config), 2.0)
        self.assertEqual(calculate_delay(3, config), 3.0)
        
    def test_calculate_delay_constant(self):
        config = RetryConfig(
            initial_delay=1.0,
            strategy=BackoffStrategy.CONSTANT
        )
        self.assertEqual(calculate_delay(1, config), 1.0)
        self.assertEqual(calculate_delay(2, config), 1.0)

    def test_sync_retry_success(self):
        mock_func = MagicMock(side_effect=[ValueError("Fail 1"), "Success"])
        config = RetryConfig(max_retries=2, initial_delay=0.01) # fast test
        
        result = execute_with_retry(mock_func, config=config)
        self.assertEqual(result, "Success")
        self.assertEqual(mock_func.call_count, 2)

    def test_sync_retry_max_retries_exceeded(self):
        mock_func = MagicMock(side_effect=ValueError("Always Fail"))
        config = RetryConfig(max_retries=2, initial_delay=0.01)
        
        with self.assertRaises(ValueError):
            execute_with_retry(mock_func, config=config)
        
        # 1 initial + 2 retries = 3 calls
        self.assertEqual(mock_func.call_count, 3)

    def test_async_retry_success(self):
        async def run():
            mock_func = AsyncMock(side_effect=[ValueError("Fail 1"), "Success"])
            config = RetryConfig(max_retries=2, initial_delay=0.01)
            
            result = await execute_with_retry_async(mock_func, config=config)
            self.assertEqual(result, "Success")
            self.assertEqual(mock_func.call_count, 2)
            
        asyncio.run(run())

    def test_on_retry_callback(self):
        mock_func = MagicMock(side_effect=[ValueError("Fail 1"), "Success"])
        config = RetryConfig(max_retries=2, initial_delay=0.01)
        mock_callback = MagicMock()
        
        execute_with_retry(mock_func, config=config, on_retry=mock_callback)
        
        mock_callback.assert_called_once()
        args = mock_callback.call_args
        self.assertEqual(args[0][0], 1) # attempt
        self.assertIsInstance(args[0][1], ValueError) # exception
        self.assertAlmostEqual(args[0][2], 0.01, delta=0.001) # delay

if __name__ == '__main__':
    unittest.main()
