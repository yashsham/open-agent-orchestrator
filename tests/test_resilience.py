import unittest
from unittest.mock import Mock, patch
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oao.runtime.resilience import execute_with_retry, execute_with_retry_async
import asyncio

class TestResilience(unittest.TestCase):

    def test_sync_retry_success(self):
        # Fail once, then succeed
        mock_func = Mock(side_effect=[ValueError("fail"), "success"])
        # Use small delay for speed
        result = execute_with_retry(
            mock_func, 
            max_retries=2, 
            initial_delay=0.001, 
            retry_on=(ValueError,)
        )
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 2)

    def test_sync_retry_exhausted(self):
        # Fail always
        mock_func = Mock(side_effect=ValueError("fail"))
        with self.assertRaises(ValueError):
            execute_with_retry(
                mock_func, 
                max_retries=2, 
                initial_delay=0.001, 
                retry_on=(ValueError,)
            )
        self.assertEqual(mock_func.call_count, 3) # Initial + 2 retries

    def test_async_retry_success(self):
        async def run_test():
            mock_func = Mock(side_effect=[ValueError("fail"), "success"])
            
            # Wrap in async partial because execute_with_retry_async expects async func
            async def async_wrapper():
                return mock_func()
                
            result = await execute_with_retry_async(
                async_wrapper, 
                max_retries=2, 
                initial_delay=0.001, 
                retry_on=(ValueError,)
            )
            self.assertEqual(result, "success")
            self.assertEqual(mock_func.call_count, 2)
            
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
