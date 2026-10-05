import time
import random
import asyncio
import functools
import logging
from typing import Callable, Tuple, Type, Optional, Any

logger = logging.getLogger("mailmind.resilience.retry")


def calculate_backoff(
    attempt: int,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    exponential_factor: float = 2.0,
    jitter: bool = True,
) -> float:
    """Calculates exponential backoff delay with jitter."""
    delay = min(max_delay, base_delay * (exponential_factor ** attempt))
    if jitter:
        # Full jitter: random uniform between 0 and delay
        delay = random.uniform(delay * 0.5, delay * 1.5)
    return min(max_delay, max(0.01, delay))


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    exponential_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
):
    """
    Decorator for retrying sync and async operations with exponential backoff and jitter.
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exc = None
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except retryable_exceptions as exc:
                        last_exc = exc
                        if attempt == max_retries:
                            logger.error(
                                "Function '%s' failed after %d retries: %s",
                                func.__name__,
                                max_retries,
                                exc,
                            )
                            raise
                        delay = calculate_backoff(
                            attempt, base_delay, max_delay, exponential_factor, jitter
                        )
                        logger.warning(
                            "Retryable failure in '%s' (attempt %d/%d). Retrying in %.2fs: %s",
                            func.__name__,
                            attempt + 1,
                            max_retries,
                            delay,
                            exc,
                        )
                        if on_retry:
                            on_retry(exc, attempt + 1, delay)
                        await asyncio.sleep(delay)
                if last_exc:
                    raise last_exc
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                last_exc = None
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except retryable_exceptions as exc:
                        last_exc = exc
                        if attempt == max_retries:
                            logger.error(
                                "Function '%s' failed after %d retries: %s",
                                func.__name__,
                                max_retries,
                                exc,
                            )
                            raise
                        delay = calculate_backoff(
                            attempt, base_delay, max_delay, exponential_factor, jitter
                        )
                        logger.warning(
                            "Retryable failure in '%s' (attempt %d/%d). Retrying in %.2fs: %s",
                            func.__name__,
                            attempt + 1,
                            max_retries,
                            delay,
                            exc,
                        )
                        if on_retry:
                            on_retry(exc, attempt + 1, delay)
                        time.sleep(delay)
                if last_exc:
                    raise last_exc
            return sync_wrapper

    return decorator
