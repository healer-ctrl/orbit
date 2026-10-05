import time
import threading
import functools
import asyncio
import logging
from enum import Enum
from typing import Callable, Any, Optional, Tuple, Type, Dict

logger = logging.getLogger("mailmind.resilience.circuit_breaker")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted while the Circuit Breaker is OPEN."""

    def __init__(self, service_name: str, cooldown_remaining: float):
        self.service_name = service_name
        self.cooldown_remaining = round(cooldown_remaining, 2)
        super().__init__(
            f"Circuit Breaker for '{service_name}' is OPEN. Fast-failing request. "
            f"Cooldown remaining: {self.cooldown_remaining}s."
        )


class CircuitBreaker:
    """
    Production-grade Thread-Safe Circuit Breaker.
    - CLOSED: Normal operation. Successes reset failure count; failures increment counter.
    - OPEN: Service tripped after reaching failure_threshold. Fast-fails for recovery_timeout duration.
    - HALF_OPEN: Trial period. Allows limited probe calls. If all succeed, transitions back to CLOSED; any failure re-trips to OPEN.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 2,
        expected_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.expected_exceptions = expected_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_state_change = time.time()
        self._last_failure_time: Optional[float] = None
        self._total_requests = 0
        self._total_failures = 0
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._evaluate_state()
            return self._state

    def _evaluate_state(self) -> None:
        """Evaluates whether an OPEN circuit should transition to HALF_OPEN."""
        now = time.time()
        if self._state == CircuitState.OPEN:
            if now - self._last_state_change >= self.recovery_timeout:
                logger.info(
                    "CircuitBreaker[%s]: Recovery timeout elapsed. Transitioning OPEN -> HALF_OPEN.",
                    self.name,
                )
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._success_count = 0
                self._last_state_change = now

    def _before_call(self) -> None:
        """Checks circuit state before executing a call. Raises exception if OPEN."""
        with self._lock:
            self._evaluate_state()
            self._total_requests += 1

            if self._state == CircuitState.OPEN:
                remaining = max(0.0, self.recovery_timeout - (time.time() - self._last_state_change))
                raise CircuitBreakerOpenException(self.name, remaining)

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpenException(
                        self.name,
                        max(0.0, self.recovery_timeout - (time.time() - self._last_state_change)),
                    )
                self._half_open_calls += 1

    def _on_success(self) -> None:
        """Records successful execution."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max_calls:
                    logger.info(
                        "CircuitBreaker[%s]: Probe calls successful (%d/%d). Transitioning HALF_OPEN -> CLOSED.",
                        self.name,
                        self._success_count,
                        self.half_open_max_calls,
                    )
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._half_open_calls = 0
                    self._last_state_change = time.time()
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def _on_failure(self, exc: Exception) -> None:
        """Records execution failure."""
        with self._lock:
            self._total_failures += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    "CircuitBreaker[%s]: Probe call failed in HALF_OPEN state (%s). Re-tripping to OPEN.",
                    self.name,
                    exc,
                )
                self._state = CircuitState.OPEN
                self._last_state_change = time.time()
                self._half_open_calls = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                logger.warning(
                    "CircuitBreaker[%s]: Call failed (%d/%d): %s",
                    self.name,
                    self._failure_count,
                    self.failure_threshold,
                    exc,
                )
                if self._failure_count >= self.failure_threshold:
                    logger.error(
                        "CircuitBreaker[%s]: Failure threshold reached (%d). Tripping circuit CLOSED -> OPEN.",
                        self.name,
                        self.failure_threshold,
                    )
                    self._state = CircuitState.OPEN
                    self._last_state_change = time.time()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Executes a synchronous function protected by this Circuit Breaker."""
        self._before_call()
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as exc:
            self._on_failure(exc)
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Executes an asynchronous function protected by this Circuit Breaker."""
        self._before_call()
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as exc:
            self._on_failure(exc)
            raise

    def get_status(self) -> Dict[str, Any]:
        """Returns diagnostic metrics and status for health probes and dashboards."""
        with self._lock:
            self._evaluate_state()
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout_sec": self.recovery_timeout,
                "total_requests": self._total_requests,
                "total_failures": self._total_failures,
                "last_state_change": self._last_state_change,
                "last_failure_time": self._last_failure_time,
            }

    def reset(self) -> None:
        """Manually resets the circuit breaker to CLOSED."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._last_state_change = time.time()
            logger.info("CircuitBreaker[%s]: Manually reset to CLOSED.", self.name)


def circuit_breaker(
    breaker: CircuitBreaker,
    fallback: Optional[Callable] = None,
):
    """
    Decorator for wrapping sync and async functions with a Circuit Breaker.
    If the circuit is open or throws expected exceptions, optional fallback can be invoked.
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await breaker.call_async(func, *args, **kwargs)
                except CircuitBreakerOpenException as cbe:
                    if fallback:
                        logger.info("CircuitBreaker[%s] open: executing async fallback.", breaker.name)
                        if asyncio.iscoroutinefunction(fallback):
                            return await fallback(*args, **kwargs)
                        return fallback(*args, **kwargs)
                    raise cbe
                except breaker.expected_exceptions as exc:
                    if fallback:
                        logger.info("CircuitBreaker[%s] error (%s): executing async fallback.", breaker.name, exc)
                        if asyncio.iscoroutinefunction(fallback):
                            return await fallback(*args, **kwargs)
                        return fallback(*args, **kwargs)
                    raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return breaker.call(func, *args, **kwargs)
                except CircuitBreakerOpenException as cbe:
                    if fallback:
                        logger.info("CircuitBreaker[%s] open: executing sync fallback.", breaker.name)
                        return fallback(*args, **kwargs)
                    raise cbe
                except breaker.expected_exceptions as exc:
                    if fallback:
                        logger.info("CircuitBreaker[%s] error (%s): executing sync fallback.", breaker.name, exc)
                        return fallback(*args, **kwargs)
                    raise
            return sync_wrapper

    return decorator
