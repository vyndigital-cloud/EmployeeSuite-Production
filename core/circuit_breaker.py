"""
Circuit Breaker Pattern - Fail fast and recover automatically
Wraps all external calls (Shopify, Database) with resilience
"""
import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from functools import wraps
from threading import Lock

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open" # Testing if service recovered

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: tuple = (Exception,)
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = Lock()
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self._call(func, *args, **kwargs)
        return wrapper
    
    def _call(self, func: Callable, *args, **kwargs) -> Any:
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker {self.name} moving to HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker {self.name} is OPEN. "
                        f"Service unavailable for {self.recovery_timeout}s"
                    )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        with self.lock:
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                logger.info(f"Circuit breaker {self.name} recovered to CLOSED")
    
    def _on_failure(self):
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(
                    f"Circuit breaker {self.name} opened after {self.failure_count} failures"
                )

class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass

# Pre-configured circuit breakers for different services
shopify_breaker = CircuitBreaker(
    name="shopify_api",
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=(Exception,)
)

database_breaker = CircuitBreaker(
    name="database",
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=(Exception,)
)

def with_circuit_breaker(breaker_name: str):
    """Decorator to apply circuit breaker by name"""
    breakers = {
        'shopify': shopify_breaker,
        'database': database_breaker
    }
    
    breaker = breakers.get(breaker_name)
    if not breaker:
        raise ValueError(f"Unknown circuit breaker: {breaker_name}")
    
    return breaker
