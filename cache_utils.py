import os
import json
import logging
import redis
from datetime import timedelta

logger = logging.getLogger(__name__)

# Initialize Redis client
# TITAN: Redis Circuit Breaker - Zero-Freeze Connectivity
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    # Strict 0.5s timeouts to prevent thread freezes
    redis_client = redis.from_url(
        REDIS_URL, 
        decode_responses=True,
        socket_timeout=0.5,
        socket_connect_timeout=0.5,
        retry_on_timeout=False
    )
    # Test connection immediately
    redis_client.ping()
    logger.info(f"TITAN [REDIS] Circuit closed. Connected to {REDIS_URL}")
except Exception as e:
    logger.critical(f"TITAN [REDIS] Circuit open. Redis unreachable at {REDIS_URL}: {e}")
    redis_client = None

def cache_set(key, value, expire=3600):
    """Set value in cache with optional expiration (default 1 hour)"""
    if not redis_client:
        return False
    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return redis_client.setex(key, expire, value)
    except Exception as e:
        logger.error(f"Redis Cache Set Error for key {key}: {e}")
        return False

def cache_get(key):
    """Get value from cache"""
    if not redis_client:
        return None
    try:
        value = redis_client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    except Exception as e:
        logger.error(f"Redis Cache Get Error for key {key}: {e}")
        return None

def cache_delete(key):
    """Delete value from cache"""
    if not redis_client:
        return False
    try:
        return redis_client.delete(key)
    except Exception as e:
        logger.error(f"Redis Cache Delete Error for key {key}: {e}")
        return False

def get_store_settings_cached(shop_domain):
    """Cache-Aside pattern for Shopify Store Settings"""
    cache_key = f"store_settings:{shop_domain}"
    
    # 1. Check Cache
    settings = cache_get(cache_key)
    if settings:
        logger.debug(f"🚀 Cache Hit: Settings for {shop_domain}")
        return settings
    
    # 2. Check DB
    from models import ShopifyStore
    store = ShopifyStore.query.filter_by(shop_url=shop_domain).first()
    if store:
        logger.debug(f"📊 Cache Miss: Fetching settings from DB for {shop_domain}")
        settings = {
            "is_active": store.is_active,
            "is_installed": store.is_installed,
            "shop_name": store.shop_name,
            "timezone": store.timezone,
            "currency": store.currency
        }
        # 3. Update Cache
        cache_set(cache_key, settings)
        return settings
    
    return None
