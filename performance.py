"""
Performance Optimizations for Employee Suite
Lightning-fast caching and response optimization
"""

from functools import wraps
from datetime import datetime, timedelta
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

# In-memory cache (simple, fast, no dependencies)
_cache = {}
_cache_timestamps = {}

# Cache TTLs (in seconds)
CACHE_TTL_INVENTORY = 60  # 1 minute for inventory
CACHE_TTL_ORDERS = 30  # 30 seconds for orders
CACHE_TTL_REPORTS = 120  # 2 minutes for reports
CACHE_TTL_STATS = 300  # 5 minutes for dashboard stats

def get_cache_key(prefix, *args, **kwargs):
    """Generate cache key from function arguments"""
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items()) if kwargs else {}
    }
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    return f"{prefix}:{key_hash}"

def cache_result(ttl=CACHE_TTL_INVENTORY):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = get_cache_key(func.__name__, *args, **kwargs)
            
            # Check cache
            if cache_key in _cache:
                timestamp = _cache_timestamps.get(cache_key)
                if timestamp and (datetime.utcnow() - timestamp).total_seconds() < ttl:
                    logger.debug(f"Cache HIT: {func.__name__}")
                    return _cache[cache_key]
                else:
                    # Expired, remove it
                    _cache.pop(cache_key, None)
                    _cache_timestamps.pop(cache_key, None)
            
            # Cache miss - execute function
            logger.debug(f"Cache MISS: {func.__name__}")
            result = func(*args, **kwargs)
            
            # Store in cache
            _cache[cache_key] = result
            _cache_timestamps[cache_key] = datetime.utcnow()
            
            return result
        return wrapper
    return decorator

def clear_cache(pattern=None):
    """Clear cache entries matching pattern"""
    if pattern is None:
        _cache.clear()
        _cache_timestamps.clear()
        logger.info("Cache cleared completely")
    else:
        keys_to_remove = [k for k in _cache.keys() if pattern in k]
        for key in keys_to_remove:
            _cache.pop(key, None)
            _cache_timestamps.pop(key, None)
        logger.info(f"Cleared {len(keys_to_remove)} cache entries matching '{pattern}'")

def get_cache_stats():
    """Get cache statistics"""
    return {
        'entries': len(_cache),
        'keys': list(_cache.keys())[:10]  # First 10 keys
    }

# Response compression
import gzip

def compress_response(response):
    """Compress response if client supports it"""
    try:
        # Get request from response context
        from flask import request
        
        # Only compress if response is large enough and client accepts gzip
        accept_encoding = request.headers.get('Accept-Encoding', '') if hasattr(request, 'headers') else ''
        
        if 'gzip' not in accept_encoding:
            return response
        
        # Only compress text-based responses
        content_type = response.content_type or ''
        if not any(x in content_type for x in ['text', 'json', 'html', 'javascript', 'css', 'xml']):
            return response
        
        # Only compress if response is > 1KB
        data = response.get_data()
        if len(data) < 1024:
            return response
        
        # Compress
        compressed = gzip.compress(data, compresslevel=6)  # Level 6 = good balance
        response.set_data(compressed)
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = len(compressed)
        response.headers['Vary'] = 'Accept-Encoding'
        logger.debug(f"Compressed response: {len(data)} -> {len(compressed)} bytes ({100*(1-len(compressed)/len(data)):.1f}% reduction)")
    except Exception as e:
        # If compression fails, return original response
        logger.debug(f"Compression skipped: {e}")
    
    return response

# Database query optimization
def optimize_query(query):
    """Optimize database query"""
    # SQLAlchemy already optimizes, but we can add hints
    return query

# Connection pooling (handled by SQLAlchemy, but we can verify settings)
def get_db_pool_settings():
    """Get optimal database pool settings"""
    return {
        'pool_size': 5,
        'max_overflow': 10,
        'pool_pre_ping': True,  # Verify connections before using
        'pool_recycle': 3600,  # Recycle connections after 1 hour
    }
