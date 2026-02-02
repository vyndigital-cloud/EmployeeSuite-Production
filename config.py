"""
Simple Configuration - No complex validation that can fail
"""

import os


# Simple config getter
def get_config():
    """Get configuration with safe defaults"""
    return {
        "SECRET_KEY": os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
        "SHOPIFY_API_KEY": os.getenv("SHOPIFY_API_KEY", ""),
        "SHOPIFY_API_SECRET": os.getenv("SHOPIFY_API_SECRET", ""),
        "DATABASE_URL": os.getenv("DATABASE_URL", "sqlite:///app.db"),
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
        "SQLALCHEMY_DATABASE_URI": os.getenv("DATABASE_URL", "sqlite:///app.db"),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": False,  # Disable to avoid import issues
        "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,
        "SHOPIFY_API_VERSION": os.getenv("SHOPIFY_API_VERSION", "2025-10"),
        "APP_URL": os.getenv(
            "APP_URL", "https://employeesuite-production.onrender.com"
        ),
        "DEBUG": os.getenv("DEBUG", "False").lower() == "true",
        "ENCRYPTION_KEY": os.getenv("ENCRYPTION_KEY", ""),
    }


class ConfigValidationError(Exception):
    pass


def get_config_safe(key, default=None):
    """Get config value with safe fallback"""
    try:
        config = get_config()
        return config.get(key, default)
    except Exception:
        return default


# Export commonly used values
config = get_config()
SHOPIFY_API_VERSION = config["SHOPIFY_API_VERSION"]
DEBUG_MODE = config["DEBUG"]
ENCRYPTION_KEY = config["ENCRYPTION_KEY"]

# Auto-scaling configuration (simplified)
AUTO_SCALING_ENGINE_OPTIONS = {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_recycle": 3600,
    "pool_timeout": 30,
    "pool_pre_ping": True,
}
