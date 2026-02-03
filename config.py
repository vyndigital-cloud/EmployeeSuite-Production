"""
Ultra-Fast Configuration - Minimal overhead
"""
import os

# Pre-compute all config values at module load time
_CONFIG_CACHE = {
    "SECRET_KEY": os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
    "SHOPIFY_API_KEY": os.getenv("SHOPIFY_API_KEY", ""),
    "SHOPIFY_API_SECRET": os.getenv("SHOPIFY_API_SECRET", ""),
    "DATABASE_URL": os.getenv("DATABASE_URL", "sqlite:///app.db"),
    "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
    "SQLALCHEMY_DATABASE_URI": os.getenv("DATABASE_URL", "sqlite:///app.db"),
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    "WTF_CSRF_ENABLED": True,
    "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,
    "SHOPIFY_API_VERSION": os.getenv("SHOPIFY_API_VERSION", "2025-10"),
    "APP_URL": os.getenv("APP_URL", os.getenv("SHOPIFY_APP_URL", "https://employeesuite-production.onrender.com")),
    "DEBUG": os.getenv("DEBUG", "False").lower() == "true",
    "ENCRYPTION_KEY": os.getenv("ENCRYPTION_KEY", ""),
}

# Fast config access
def get_config():
    """Return pre-computed config"""
    return _CONFIG_CACHE

def get_config_safe(key, default=None):
    """Ultra-fast config getter"""
    return _CONFIG_CACHE.get(key, default)

# Direct exports for fastest access
config = _CONFIG_CACHE
SHOPIFY_API_VERSION = _CONFIG_CACHE["SHOPIFY_API_VERSION"]
DEBUG_MODE = _CONFIG_CACHE["DEBUG"]
ENCRYPTION_KEY = _CONFIG_CACHE["ENCRYPTION_KEY"]

# Optimized database settings
AUTO_SCALING_ENGINE_OPTIONS = {
    "pool_size": 5,        # Reduced from 10
    "max_overflow": 10,    # Reduced from 20
    "pool_recycle": 1800,  # Reduced from 3600
    "pool_timeout": 15,    # Reduced from 30
    "pool_pre_ping": True,
    "echo": False,         # Disable SQL logging for speed
}

class ConfigValidationError(Exception):
    pass
