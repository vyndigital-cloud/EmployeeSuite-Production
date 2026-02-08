"""
Ultra-Fast Configuration - Minimal overhead
"""
import os

# Pre-compute all config values at module load time
_CONFIG_CACHE = {
    "SECRET_KEY": os.getenv("SECRET_KEY"),  # Must be set in environment
    "SHOPIFY_API_KEY": os.getenv("SHOPIFY_API_KEY", ""),
    "SHOPIFY_API_SECRET": os.getenv("SHOPIFY_API_SECRET", ""),
    "SHOPIFY_APP_HANDLE": os.getenv("SHOPIFY_APP_HANDLE", "employee-suite-7"),  # True app handle from Partners Dashboard
    "DATABASE_URL": os.getenv("DATABASE_URL", "sqlite:///app.db"),
    "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
    "SQLALCHEMY_DATABASE_URI": os.getenv("DATABASE_URL", "sqlite:///app.db"),
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    "WTF_CSRF_ENABLED": True,
    "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,
    "SHOPIFY_API_VERSION": os.getenv("SHOPIFY_API_VERSION", "2025-10"),
    "BASE_URL": os.getenv("BASE_URL", os.getenv("APP_URL", "https://employeesuite-production.onrender.com")).rstrip("/"),
    "APP_URL": os.getenv("APP_URL", os.getenv("SHOPIFY_APP_URL", "https://employeesuite-production.onrender.com")).rstrip("/"),
    "DEBUG": os.getenv("DEBUG", "False").lower() == "true",
    "ENCRYPTION_KEY": os.getenv("ENCRYPTION_KEY", ""),
    "SENDGRID_API_KEY": os.getenv("SENDGRID_API_KEY", ""),
    
    # Session Configuration (Server-Side)
    "SESSION_TYPE": "redis" if os.getenv("REDIS_URL") else "sqlalchemy",
    "SESSION_PERMANENT": True,
    "SESSION_USE_SIGNER": True,
    "SESSION_KEY_PREFIX": "missioncontrol:session:",
    "SESSION_REDIS": None,  # Will be set in app_factory if using redis
    # Allow over-riding session type for local/testing
    "SESSION_TYPE_FORCE": os.getenv("SESSION_TYPE", ""),
}

# Critical Security Check
if _CONFIG_CACHE["SECRET_KEY"] == "dev-secret-key-change-in-production" and _CONFIG_CACHE["ENVIRONMENT"] == "production":
    print("⚠️  WARNING: Running in PRODUCTION with default SECRET_KEY! Sessions will be invalidated on restart!")


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
SENDGRID_API_KEY = _CONFIG_CACHE["SENDGRID_API_KEY"]

# Optimized database settings
AUTO_SCALING_ENGINE_OPTIONS = {
    "pool_size": 5,        # Reduced from 10
    "max_overflow": 10,    # Reduced from 20
    "pool_recycle": 1800,  # Reduced from 3600
    "pool_timeout": 15,    # Reduced from 30
    "pool_pre_ping": True,
    "echo": False,         # Disable SQL logging for speed
}

def validate_email_config():
    """Validate email configuration on startup"""
    import logging
    logger = logging.getLogger(__name__)
    
    issues = []
    
    if not get_config_safe("SENDGRID_API_KEY"):
        issues.append("SENDGRID_API_KEY not set")
    
    if not get_config_safe("SMTP_USERNAME") and not get_config_safe("SENDGRID_API_KEY"):
        issues.append("No email service configured (neither SendGrid nor SMTP)")
    
    if issues:
        logger.warning(f"Email configuration issues: {', '.join(issues)}")
    
    return len(issues) == 0

# Call this in app startup
EMAIL_CONFIG_VALID = validate_email_config()

class ConfigValidationError(Exception):
    pass
"""
Configuration Management
"""
import os
from typing import Any, Optional

def get_config_safe(key: str, default: Any = None) -> Any:
    """
    Safely get configuration value with fallback
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        Configuration value or default
    """
    try:
        value = os.getenv(key, default)
        
        # Handle boolean strings
        if isinstance(value, str):
            if value.lower() in ('true', '1', 'yes', 'on'):
                return True
            elif value.lower() in ('false', '0', 'no', 'off'):
                return False
                
        return value
    except Exception:
        return default

# Shopify API Configuration
SHOPIFY_API_VERSION = "2024-01"
SHOPIFY_API_KEY = get_config_safe("SHOPIFY_API_KEY", "")
SHOPIFY_API_SECRET = get_config_safe("SHOPIFY_API_SECRET", "")

# Database Configuration
DATABASE_URL = get_config_safe("DATABASE_URL", "sqlite:///employeesuite.db")

# App Configuration
SECRET_KEY = get_config_safe("SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = get_config_safe("DEBUG", False)
ENVIRONMENT = get_config_safe("ENVIRONMENT", "development")

# Security Configuration
ENCRYPTION_KEY = get_config_safe("ENCRYPTION_KEY", "")
CSRF_SECRET_KEY = get_config_safe("CSRF_SECRET_KEY", SECRET_KEY)

# Email Configuration
SMTP_SERVER = get_config_safe("SMTP_SERVER", "")
SMTP_PORT = get_config_safe("SMTP_PORT", 587)
SMTP_USERNAME = get_config_safe("SMTP_USERNAME", "")
SMTP_PASSWORD = get_config_safe("SMTP_PASSWORD", "")

# Logging Configuration
LOG_LEVEL = get_config_safe("LOG_LEVEL", "INFO")
UPLOAD_FOLDER = get_config_safe("UPLOAD_FOLDER", "uploads")

# Performance Configuration
CACHE_TYPE = get_config_safe("CACHE_TYPE", "simple")
CACHE_DEFAULT_TIMEOUT = get_config_safe("CACHE_DEFAULT_TIMEOUT", 300)

# Testing Configuration
TESTING = get_config_safe("TESTING", False)
