"""
Circuit breaker for production deployment with actual circuit breaking
"""

import logging
import time
from functools import wraps
from collections import defaultdict

logger = logging.getLogger(__name__)

# Simple circuit state tracking
_circuit_states = defaultdict(lambda: {'failures': 0, 'last_failure': 0, 'state': 'closed'})
FAILURE_THRESHOLD = 5
TIMEOUT_SECONDS = 60


def with_circuit_breaker(name, fallback_data=None):
    """Actual circuit breaker with state management"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            circuit = _circuit_states[name]
            now = time.time()
            
            # Check if circuit should reset
            if circuit['state'] == 'open' and (now - circuit['last_failure']) > TIMEOUT_SECONDS:
                circuit['state'] = 'half-open'
                circuit['failures'] = 0
            
            # If circuit is open, return fallback immediately
            if circuit['state'] == 'open':
                logger.warning(f"Circuit {name} is OPEN, returning fallback")
                return fallback_data
            
            try:
                result = func(*args, **kwargs)
                # Success - reset circuit
                if circuit['failures'] > 0:
                    circuit['failures'] = 0
                    circuit['state'] = 'closed'
                return result
                
            except Exception as e:
                circuit['failures'] += 1
                circuit['last_failure'] = now
                
                # Open circuit if threshold reached
                if circuit['failures'] >= FAILURE_THRESHOLD:
                    circuit['state'] = 'open'
                    logger.error(f"Circuit {name} OPENED after {circuit['failures']} failures")
                
                logger.error(f"{name} operation failed: {e}")
                
                # Return fallback or re-raise based on circuit state
                if circuit['state'] == 'open' and fallback_data is not None:
                    return fallback_data
                raise
                
        return wrapper
    return decorator


def database_breaker(func):
    """Database circuit breaker with fallback"""
    return with_circuit_breaker("database", fallback_data=None)(func)


def shopify_breaker(func):
    """Shopify circuit breaker with fallback"""
    return with_circuit_breaker("shopify", fallback_data={"error": "Shopify temporarily unavailable"})(func)
