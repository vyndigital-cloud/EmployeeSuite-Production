"""
Simplified circuit breaker for production deployment
"""

import logging
from functools import wraps

logger = logging.getLogger(__name__)


def database_breaker(func):
    """Simplified database circuit breaker"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise

    return wrapper


def shopify_breaker(func):
    """Simplified Shopify circuit breaker"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Shopify operation failed: {e}")
            raise

    return wrapper


def with_circuit_breaker(name):
    """Generic circuit breaker decorator"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{name} operation failed: {e}")
                raise

        return wrapper

    return decorator
