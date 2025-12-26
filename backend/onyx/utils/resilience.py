"""
Enterprise-grade resilience utilities for the Onyx RAG pipeline.

Provides:
- Circuit breaker pattern for external service calls (Vespa, LLM, embedding)
- Retry with exponential backoff and jitter
- Graceful degradation strategies
- Request timeout management
"""

import functools
import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import Generic
from typing import TypeVar

from onyx.utils.logger import setup_logger

logger = setup_logger()

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    # Number of failures before opening circuit
    failure_threshold: int = 5
    # Time in seconds to wait before attempting recovery
    recovery_timeout: float = 30.0
    # Number of successful calls needed to close circuit from half-open
    success_threshold: int = 2
    # Exceptions that should trigger the circuit breaker
    expected_exceptions: tuple[type[Exception], ...] = (Exception,)
    # Name for logging/metrics
    name: str = "default"


@dataclass
class CircuitBreakerState:
    """Mutable state for a circuit breaker instance."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    lock: threading.RLock = field(default_factory=threading.RLock)


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and rejecting requests."""
    def __init__(self, name: str, message: str = "Circuit breaker is open"):
        self.name = name
        super().__init__(f"[{name}] {message}")


class CircuitBreaker(Generic[T]):
    """
    Thread-safe circuit breaker implementation.
    
    Usage:
        cb = CircuitBreaker(config=CircuitBreakerConfig(name="vespa"))
        
        @cb
        def call_vespa():
            ...
            
        # Or use directly:
        result = cb.call(lambda: vespa_client.search(...))
    """
    
    # Global registry of circuit breakers for monitoring
    _registry: dict[str, "CircuitBreaker"] = {}
    _registry_lock = threading.Lock()
    
    def __init__(self, config: CircuitBreakerConfig | None = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState()
        
        # Register for monitoring
        with CircuitBreaker._registry_lock:
            CircuitBreaker._registry[self.config.name] = self
    
    @classmethod
    def get_all_states(cls) -> dict[str, dict[str, Any]]:
        """Get status of all registered circuit breakers for monitoring."""
        with cls._registry_lock:
            return {
                name: cb.get_state()
                for name, cb in cls._registry.items()
            }
    
    def get_state(self) -> dict[str, Any]:
        """Get current state for monitoring/metrics."""
        with self._state.lock:
            return {
                "name": self.config.name,
                "state": self._state.state.value,
                "failure_count": self._state.failure_count,
                "success_count": self._state.success_count,
                "last_failure_time": self._state.last_failure_time,
            }
    
    def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on circuit state."""
        with self._state.lock:
            if self._state.state == CircuitState.CLOSED:
                return True
            
            if self._state.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                elapsed = time.monotonic() - self._state.last_failure_time
                if elapsed >= self.config.recovery_timeout:
                    logger.info(
                        f"Circuit breaker [{self.config.name}] transitioning to HALF_OPEN "
                        f"after {elapsed:.1f}s"
                    )
                    self._state.state = CircuitState.HALF_OPEN
                    self._state.success_count = 0
                    return True
                return False
            
            # HALF_OPEN: allow limited requests
            return True
    
    def _record_success(self) -> None:
        """Record a successful call."""
        with self._state.lock:
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count += 1
                if self._state.success_count >= self.config.success_threshold:
                    logger.info(
                        f"Circuit breaker [{self.config.name}] closing after "
                        f"{self._state.success_count} successful calls"
                    )
                    self._state.state = CircuitState.CLOSED
                    self._state.failure_count = 0
                    self._state.success_count = 0
            elif self._state.state == CircuitState.CLOSED:
                # Reset failure count on success
                self._state.failure_count = 0
    
    def _record_failure(self, exc: Exception) -> None:
        """Record a failed call."""
        with self._state.lock:
            self._state.failure_count += 1
            self._state.last_failure_time = time.monotonic()
            
            if self._state.state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens the circuit
                logger.warning(
                    f"Circuit breaker [{self.config.name}] reopening due to failure in HALF_OPEN: {exc}"
                )
                self._state.state = CircuitState.OPEN
                self._state.success_count = 0
            elif self._state.state == CircuitState.CLOSED:
                if self._state.failure_count >= self.config.failure_threshold:
                    logger.warning(
                        f"Circuit breaker [{self.config.name}] opening after "
                        f"{self._state.failure_count} failures"
                    )
                    self._state.state = CircuitState.OPEN
    
    def call(self, func: Callable[[], T], fallback: Callable[[], T] | None = None) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: The function to execute
            fallback: Optional fallback function if circuit is open
            
        Returns:
            Result from func or fallback
            
        Raises:
            CircuitBreakerError: If circuit is open and no fallback provided
        """
        if not self._should_allow_request():
            if fallback is not None:
                logger.info(f"Circuit breaker [{self.config.name}] using fallback")
                return fallback()
            raise CircuitBreakerError(self.config.name)
        
        try:
            result = func()
            self._record_success()
            return result
        except self.config.expected_exceptions as e:
            self._record_failure(e)
            raise
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator form of the circuit breaker."""
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return self.call(lambda: func(*args, **kwargs))
        return wrapper
    
    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        with self._state.lock:
            self._state.state = CircuitState.CLOSED
            self._state.failure_count = 0
            self._state.success_count = 0
            logger.info(f"Circuit breaker [{self.config.name}] manually reset")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: float = 0.1  # Fraction of delay to randomize
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)


def retry_with_backoff(
    config: RetryConfig | None = None,
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retry with exponential backoff and jitter.
    
    Args:
        config: Retry configuration
        on_retry: Callback called on each retry (attempt, exception, delay)
        
    Usage:
        @retry_with_backoff(RetryConfig(max_attempts=5))
        def flaky_operation():
            ...
    """
    config = config or RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts:
                        logger.error(
                            f"Retry exhausted after {attempt} attempts for {func.__name__}: {e}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** (attempt - 1)),
                        config.max_delay,
                    )
                    
                    # Add jitter
                    jitter_amount = delay * config.jitter
                    delay += random.uniform(-jitter_amount, jitter_amount)
                    delay = max(0, delay)
                    
                    logger.warning(
                        f"Retry {attempt}/{config.max_attempts} for {func.__name__} "
                        f"after {delay:.2f}s: {e}"
                    )
                    
                    if on_retry:
                        on_retry(attempt, e, delay)
                    
                    time.sleep(delay)
            
            # Should not reach here, but satisfy type checker
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")
        
        return wrapper
    return decorator


class GracefulDegradation:
    """
    Manages graceful degradation strategies for the RAG pipeline.
    
    Provides fallback behaviors when primary services are unavailable.
    """
    
    def __init__(self) -> None:
        self._degradation_modes: dict[str, bool] = {}
        self._lock = threading.Lock()
    
    def is_degraded(self, service: str) -> bool:
        """Check if a service is in degraded mode."""
        with self._lock:
            return self._degradation_modes.get(service, False)
    
    def set_degraded(self, service: str, degraded: bool = True) -> None:
        """Set degradation mode for a service."""
        with self._lock:
            self._degradation_modes[service] = degraded
            if degraded:
                logger.warning(f"Service [{service}] entering degraded mode")
            else:
                logger.info(f"Service [{service}] exiting degraded mode")
    
    def get_all_statuses(self) -> dict[str, bool]:
        """Get degradation status for all services."""
        with self._lock:
            return dict(self._degradation_modes)


# Global instances for the RAG pipeline
vespa_circuit_breaker = CircuitBreaker(
    CircuitBreakerConfig(
        name="vespa",
        failure_threshold=5,
        recovery_timeout=30.0,
        success_threshold=2,
    )
)

embedding_circuit_breaker = CircuitBreaker(
    CircuitBreakerConfig(
        name="embedding",
        failure_threshold=3,
        recovery_timeout=60.0,
        success_threshold=1,
    )
)

llm_circuit_breaker = CircuitBreaker(
    CircuitBreakerConfig(
        name="llm",
        failure_threshold=3,
        recovery_timeout=60.0,
        success_threshold=1,
    )
)

degradation_manager = GracefulDegradation()


# Convenience retry configurations
VESPA_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=0.2,
)

EMBEDDING_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=0.1,
)

LLM_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    base_delay=2.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=0.1,
)
