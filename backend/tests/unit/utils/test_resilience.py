"""
Unit tests for resilience utilities (circuit breaker, retry, graceful degradation).
"""

import threading
import time
from unittest.mock import MagicMock

import pytest

from onyx.utils.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
    GracefulDegradation,
    retry_with_backoff,
    RetryConfig,
)


class TestCircuitBreaker:
    """Tests for circuit breaker implementation."""
    
    def test_closed_state_allows_requests(self) -> None:
        """Circuit breaker in closed state should allow requests."""
        cb = CircuitBreaker(CircuitBreakerConfig(name="test_closed"))
        
        call_count = 0
        def successful_call() -> str:
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = cb.call(successful_call)
        
        assert result == "success"
        assert call_count == 1
        assert cb.get_state()["state"] == "closed"
    
    def test_opens_after_failure_threshold(self) -> None:
        """Circuit should open after reaching failure threshold."""
        cb = CircuitBreaker(CircuitBreakerConfig(
            name="test_open",
            failure_threshold=3,
            recovery_timeout=60.0,
        ))
        
        def failing_call() -> None:
            raise ValueError("Simulated failure")
        
        # Cause failures up to threshold
        for i in range(3):
            with pytest.raises(ValueError):
                cb.call(failing_call)
        
        assert cb.get_state()["state"] == "open"
        assert cb.get_state()["failure_count"] == 3
    
    def test_open_circuit_rejects_requests(self) -> None:
        """Open circuit should reject requests with CircuitBreakerError."""
        cb = CircuitBreaker(CircuitBreakerConfig(
            name="test_reject",
            failure_threshold=1,
            recovery_timeout=60.0,
        ))
        
        # Open the circuit
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        
        # Next call should be rejected
        with pytest.raises(CircuitBreakerError) as exc_info:
            cb.call(lambda: "should not execute")
        
        assert "test_reject" in str(exc_info.value)
    
    def test_fallback_when_open(self) -> None:
        """Should use fallback function when circuit is open."""
        cb = CircuitBreaker(CircuitBreakerConfig(
            name="test_fallback",
            failure_threshold=1,
            recovery_timeout=60.0,
        ))
        
        # Open the circuit
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        
        # Should use fallback
        result = cb.call(
            lambda: "primary",
            fallback=lambda: "fallback_result",
        )
        
        assert result == "fallback_result"
    
    def test_half_open_after_recovery_timeout(self) -> None:
        """Circuit should transition to half-open after recovery timeout."""
        cb = CircuitBreaker(CircuitBreakerConfig(
            name="test_half_open",
            failure_threshold=1,
            recovery_timeout=0.1,  # 100ms for fast test
        ))
        
        # Open the circuit
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        
        assert cb.get_state()["state"] == "open"
        
        # Wait for recovery timeout
        time.sleep(0.15)
        
        # Next call should be allowed (half-open)
        result = cb.call(lambda: "recovered")
        assert result == "recovered"
    
    def test_closes_after_success_in_half_open(self) -> None:
        """Circuit should close after successful calls in half-open state."""
        cb = CircuitBreaker(CircuitBreakerConfig(
            name="test_close",
            failure_threshold=1,
            recovery_timeout=0.05,
            success_threshold=2,
        ))
        
        # Open the circuit
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        
        time.sleep(0.1)
        
        # First success
        cb.call(lambda: "success1")
        assert cb.get_state()["state"] == "half_open"
        
        # Second success should close
        cb.call(lambda: "success2")
        assert cb.get_state()["state"] == "closed"
    
    def test_reopens_on_failure_in_half_open(self) -> None:
        """Circuit should reopen if failure occurs in half-open state."""
        cb = CircuitBreaker(CircuitBreakerConfig(
            name="test_reopen",
            failure_threshold=1,
            recovery_timeout=0.05,
        ))
        
        # Open the circuit
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        
        time.sleep(0.1)
        
        # Fail in half-open
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail again")))
        
        assert cb.get_state()["state"] == "open"
    
    def test_manual_reset(self) -> None:
        """Should be able to manually reset circuit breaker."""
        cb = CircuitBreaker(CircuitBreakerConfig(
            name="test_reset",
            failure_threshold=1,
        ))
        
        # Open the circuit
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        
        assert cb.get_state()["state"] == "open"
        
        cb.reset()
        assert cb.get_state()["state"] == "closed"
        assert cb.get_state()["failure_count"] == 0
    
    def test_decorator_usage(self) -> None:
        """Circuit breaker should work as a decorator."""
        cb = CircuitBreaker(CircuitBreakerConfig(name="test_decorator"))
        
        call_count = 0
        
        @cb
        def decorated_function() -> str:
            nonlocal call_count
            call_count += 1
            return "decorated"
        
        result = decorated_function()
        
        assert result == "decorated"
        assert call_count == 1
    
    def test_thread_safety(self) -> None:
        """Circuit breaker should be thread-safe."""
        cb = CircuitBreaker(CircuitBreakerConfig(
            name="test_threadsafe",
            failure_threshold=50,
        ))
        
        success_count = 0
        lock = threading.Lock()
        
        def concurrent_call() -> None:
            nonlocal success_count
            try:
                cb.call(lambda: "ok")
                with lock:
                    success_count += 1
            except Exception:
                pass
        
        threads = [threading.Thread(target=concurrent_call) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert success_count == 100
    
    def test_registry_tracking(self) -> None:
        """All circuit breakers should be tracked in registry."""
        cb1 = CircuitBreaker(CircuitBreakerConfig(name="registry_test_1"))
        cb2 = CircuitBreaker(CircuitBreakerConfig(name="registry_test_2"))
        
        states = CircuitBreaker.get_all_states()
        
        assert "registry_test_1" in states
        assert "registry_test_2" in states


class TestRetryWithBackoff:
    """Tests for retry with exponential backoff."""
    
    def test_succeeds_on_first_try(self) -> None:
        """Should return immediately on success."""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(max_attempts=3))
        def successful_call() -> str:
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_call()
        
        assert result == "success"
        assert call_count == 1
    
    def test_retries_on_failure(self) -> None:
        """Should retry on failure up to max_attempts."""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(
            max_attempts=3,
            base_delay=0.01,
            max_delay=0.1,
        ))
        def flaky_call() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = flaky_call()
        
        assert result == "success"
        assert call_count == 3
    
    def test_raises_after_exhausting_retries(self) -> None:
        """Should raise exception after exhausting all retries."""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(
            max_attempts=3,
            base_delay=0.01,
        ))
        def always_fails() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent failure")
        
        with pytest.raises(ValueError, match="Persistent failure"):
            always_fails()
        
        assert call_count == 3
    
    def test_respects_retryable_exceptions(self) -> None:
        """Should only retry on specified exception types."""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=(ValueError,),
        ))
        def fails_with_type_error() -> None:
            nonlocal call_count
            call_count += 1
            raise TypeError("Not retryable")
        
        with pytest.raises(TypeError):
            fails_with_type_error()
        
        # Should not retry for TypeError
        assert call_count == 1
    
    def test_callback_on_retry(self) -> None:
        """Should call callback on each retry."""
        retry_info: list[tuple[int, str, float]] = []
        
        def on_retry(attempt: int, exc: Exception, delay: float) -> None:
            retry_info.append((attempt, str(exc), delay))
        
        @retry_with_backoff(
            RetryConfig(max_attempts=3, base_delay=0.01),
            on_retry=on_retry,
        )
        def flaky() -> str:
            if len(retry_info) < 2:
                raise ValueError("fail")
            return "ok"
        
        flaky()
        
        assert len(retry_info) == 2
        assert retry_info[0][0] == 1  # First retry
        assert retry_info[1][0] == 2  # Second retry
    
    def test_exponential_backoff(self) -> None:
        """Delays should increase exponentially."""
        delays: list[float] = []
        
        def capture_delay(attempt: int, exc: Exception, delay: float) -> None:
            delays.append(delay)
        
        call_count = 0
        
        @retry_with_backoff(
            RetryConfig(
                max_attempts=4,
                base_delay=0.1,
                exponential_base=2.0,
                jitter=0.0,  # No jitter for predictable test
            ),
            on_retry=capture_delay,
        )
        def always_fail() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")
        
        with pytest.raises(ValueError):
            always_fail()
        
        # Delays should be approximately 0.1, 0.2, 0.4
        assert len(delays) == 3
        assert 0.08 < delays[0] < 0.12  # ~0.1
        assert 0.18 < delays[1] < 0.22  # ~0.2
        assert 0.38 < delays[2] < 0.42  # ~0.4


class TestGracefulDegradation:
    """Tests for graceful degradation manager."""
    
    def test_default_not_degraded(self) -> None:
        """Services should not be degraded by default."""
        gd = GracefulDegradation()
        
        assert gd.is_degraded("vespa") is False
        assert gd.is_degraded("embedding") is False
    
    def test_set_degraded(self) -> None:
        """Should be able to set degradation mode."""
        gd = GracefulDegradation()
        
        gd.set_degraded("vespa", True)
        
        assert gd.is_degraded("vespa") is True
        assert gd.is_degraded("embedding") is False
    
    def test_clear_degraded(self) -> None:
        """Should be able to clear degradation mode."""
        gd = GracefulDegradation()
        
        gd.set_degraded("vespa", True)
        gd.set_degraded("vespa", False)
        
        assert gd.is_degraded("vespa") is False
    
    def test_get_all_statuses(self) -> None:
        """Should return all service statuses."""
        gd = GracefulDegradation()
        
        gd.set_degraded("vespa", True)
        gd.set_degraded("llm", False)
        
        statuses = gd.get_all_statuses()
        
        assert statuses["vespa"] is True
        assert statuses["llm"] is False
    
    def test_thread_safety(self) -> None:
        """Graceful degradation should be thread-safe."""
        gd = GracefulDegradation()
        
        def toggle_service() -> None:
            for _ in range(100):
                gd.set_degraded("test_service", True)
                gd.is_degraded("test_service")
                gd.set_degraded("test_service", False)
        
        threads = [threading.Thread(target=toggle_service) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should complete without errors
        assert gd.is_degraded("test_service") is False
