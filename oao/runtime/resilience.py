import time
import asyncio
import logging
import random
from enum import Enum
from typing import Callable, Type, Tuple, Any, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class BackoffStrategy(str, Enum):
    CONSTANT = "CONSTANT"
    LINEAR = "LINEAR"
    EXPONENTIAL = "EXPONENTIAL"
    JITTER = "JITTER"

@dataclass
class RetryConfig:
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    retryable_errors: Tuple[Type[Exception], ...] = (Exception,)
    non_retryable_errors: Tuple[Type[Exception], ...] = ()

def calculate_delay(attempt: int, config: RetryConfig) -> float:
    if config.strategy == BackoffStrategy.CONSTANT:
        delay = config.initial_delay
    elif config.strategy == BackoffStrategy.LINEAR:
        delay = config.initial_delay * attempt
    elif config.strategy == BackoffStrategy.EXPONENTIAL:
        delay = config.initial_delay * (config.backoff_factor ** (attempt - 1))
    elif config.strategy == BackoffStrategy.JITTER:
        base = config.initial_delay * (config.backoff_factor ** (attempt - 1))
        delay = base * random.uniform(0.5, 1.5)
    else:
        delay = config.initial_delay
        
    return min(delay, config.max_delay)

def should_retry(e: Exception, config: RetryConfig) -> bool:
    # Check non-retryable first
    if isinstance(e, config.non_retryable_errors):
        return False
    # Check retryable
    return isinstance(e, config.retryable_errors)

def execute_with_retry(
    func: Callable,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    *args, 
    **kwargs
) -> Any:
    """
    Execute a synchronous function with configurable retries.
    """
    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(1, config.max_retries + 2):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if not should_retry(e, config):
                raise e
                
            last_exception = e
            
            if attempt <= config.max_retries:
                delay = calculate_delay(attempt, config)
                func_name = getattr(func, "__name__", str(func))
                logger.warning(
                    f"Attempt {attempt}/{config.max_retries} failed for {func_name}: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                
                if on_retry:
                    try:
                        on_retry(attempt, e, delay)
                    except Exception as logging_err:
                        logger.error(f"Error in on_retry callback: {logging_err}")

                time.sleep(delay)
            else:
                func_name = getattr(func, "__name__", str(func))
                logger.error(f"All {config.max_retries} attempts failed for {func_name}.")
                
    if last_exception:
        raise last_exception

async def execute_with_retry_async(
    func: Callable,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    *args, 
    **kwargs
) -> Any:
    """
    Execute an asynchronous function with configurable retries.
    """
    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(1, config.max_retries + 2):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            if not should_retry(e, config):
                raise e
                
            last_exception = e
            
            if attempt <= config.max_retries:
                delay = calculate_delay(attempt, config)
                func_name = getattr(func, "__name__", str(func))
                logger.warning(
                    f"Attempt {attempt}/{config.max_retries} failed for {func_name}: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                
                if on_retry:
                    try:
                        on_retry(attempt, e, delay)
                    except Exception as logging_err:
                        logger.error(f"Error in on_retry callback: {logging_err}")

                await asyncio.sleep(delay)
            else:
                func_name = getattr(func, "__name__", str(func))
                logger.error(f"All {config.max_retries} attempts failed for {func_name}.")

    if last_exception:
        raise last_exception
