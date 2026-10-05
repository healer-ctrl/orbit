import time
import pytest
from backend.resilience import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenException,
    retry_with_backoff,
    calculate_backoff,
    resilience_registry,
)


def test_circuit_breaker_closed_to_open_transition():
    cb = CircuitBreaker(
        name="test_service",
        failure_threshold=3,
        recovery_timeout=0.2,
        half_open_max_calls=2,
    )

    assert cb.state == CircuitState.CLOSED

    # Failure 1
    with pytest.raises(ValueError):
        cb.call(lambda: (_ for _ in ()).throw(ValueError("Error 1")))
    assert cb.state == CircuitState.CLOSED

    # Failure 2
    with pytest.raises(ValueError):
        cb.call(lambda: (_ for _ in ()).throw(ValueError("Error 2")))
    assert cb.state == CircuitState.CLOSED

    # Failure 3 -> Trips to OPEN
    with pytest.raises(ValueError):
        cb.call(lambda: (_ for _ in ()).throw(ValueError("Error 3")))
    assert cb.state == CircuitState.OPEN

    # Fast-fails immediately when OPEN
    with pytest.raises(CircuitBreakerOpenException) as exc_info:
        cb.call(lambda: "should not run")
    assert "is OPEN" in str(exc_info.value)


def test_circuit_breaker_half_open_recovery():
    cb = CircuitBreaker(
        name="test_recovery",
        failure_threshold=2,
        recovery_timeout=0.1,  # 100ms cooldown for fast test
        half_open_max_calls=2,
    )

    # Trip the breaker
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("Fail")))

    assert cb.state == CircuitState.OPEN

    # Wait for cooldown to elapse
    time.sleep(0.12)
    assert cb.state == CircuitState.HALF_OPEN

    # Successful probe call 1
    res1 = cb.call(lambda: "probe_1_ok")
    assert res1 == "probe_1_ok"
    assert cb.state == CircuitState.HALF_OPEN

    # Successful probe call 2 -> Transitions back to CLOSED
    res2 = cb.call(lambda: "probe_2_ok")
    assert res2 == "probe_2_ok"
    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_half_open_retrip():
    cb = CircuitBreaker(
        name="test_retrip",
        failure_threshold=2,
        recovery_timeout=0.1,
        half_open_max_calls=2,
    )

    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("Fail")))

    time.sleep(0.12)
    assert cb.state == CircuitState.HALF_OPEN

    # Failed probe call in HALF_OPEN -> Re-trips immediately to OPEN
    with pytest.raises(RuntimeError):
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError("Probe failed")))

    assert cb.state == CircuitState.OPEN


def test_retry_with_backoff_success_after_retries():
    attempts = 0

    @retry_with_backoff(max_retries=3, base_delay=0.01, max_delay=0.05, jitter=False)
    def flaky_function():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionResetError("Temporary network blip")
        return "SUCCESS"

    result = flaky_function()
    assert result == "SUCCESS"
    assert attempts == 3


def test_calculate_backoff():
    d0 = calculate_backoff(0, base_delay=1.0, max_delay=10.0, exponential_factor=2.0, jitter=False)
    d1 = calculate_backoff(1, base_delay=1.0, max_delay=10.0, exponential_factor=2.0, jitter=False)
    d2 = calculate_backoff(2, base_delay=1.0, max_delay=10.0, exponential_factor=2.0, jitter=False)

    assert d0 == 1.0
    assert d1 == 2.0
    assert d2 == 4.0


def test_resilience_registry():
    statuses = resilience_registry.get_all_statuses()
    assert "azure_openai" in statuses
    assert "azure_search" in statuses
    assert "graph_api" in statuses
    assert "cosmos_db" in statuses
    assert "teams_webhook" in statuses

    for name, status in statuses.items():
        assert status["state"] in ["CLOSED", "OPEN", "HALF_OPEN"]
        assert "failure_threshold" in status
