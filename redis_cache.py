"""
Enterprise Redis Caching System
Implements distributed caching for 100k+ users
"""

import json
import logging
import os
import pickle
from datetime import timedelta
from functools import wraps

import redis

logger = logging.getLogger(__name__)


class EnterpriseCache:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = redis.from_url(
            redis_url,
            decode_responses=False,  # Handle binary data
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )

        # Test connection
        try:
            self.redis_client.ping()
            logger.info("✅ Redis connection established")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.redis_client = None

    def get(self, key):
        """Get value from cache"""
        if not self.redis_client:
            return None

        try:
            data = self.redis_client.get(f"employeesuite:{key}")
            if data:
                return pickle.loads(data)
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
        return None

    def set(self, key, value, ttl=3600):
        """Set value in cache with TTL"""
        if not self.redis_client:
            return False

        try:
            serialized = pickle.dumps(value)
            return self.redis_client.setex(f"employeesuite:{key}", ttl, serialized)
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")
            return False

    def delete(self, key):
        """Delete key from cache"""
        if not self.redis_client:
            return False

        try:
            return self.redis_client.delete(f"employeesuite:{key}")
        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")
            return False


# Global cache instance
cache = EnterpriseCache()


def cached(ttl=3600, key_prefix=""):
    """Enterprise caching decorator"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

            # Try cache first
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator
