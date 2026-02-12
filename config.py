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
    "DEV_SHOP_DOMAIN": os.getenv("DEV_SHOP_DOMAIN", "test-shop.myshopify.com"),
    "ADMIN_EMAIL": os.getenv("ADMIN_EMAIL", "essentials@example.com"),
    "LOG_LEVEL": "CRITICAL",
    
    # Session Configuration (Server-Side)
    "SESSION_TYPE": "redis" if os.getenv("REDIS_URL") else "sqlalchemy",
    "SESSION_PERMANENT": True,
    "SESSION_USE_SIGNER": True,
    "SESSION_KEY_PREFIX": "missioncontrol:session:",
    "SESSION_REDIS": None,  # Will be set in app_factory if using redis
    "SESSION_TYPE_FORCE": os.getenv("SESSION_TYPE", ""),
    
    # Global Cookie Hardening (Fix 14)
    "SESSION_COOKIE_SAMESITE": "None",
    "SESSION_COOKIE_SECURE": True,
    "REMEMBER_COOKIE_SAMESITE": "None",
    "REMEMBER_COOKIE_SECURE": True,
    "SESSION_COOKIE_HTTPONLY": True,
    
    # Pre-Ping Database Guard (Triangle of Persistence)
    "SQLALCHEMY_ENGINE_OPTIONS": {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    },
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
DEV_SHOP_DOMAIN = _CONFIG_CACHE["DEV_SHOP_DOMAIN"]
ADMIN_EMAIL = _CONFIG_CACHE["ADMIN_EMAIL"]

# Production-grade database connection pool settings (prevents SSL connection errors)
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,       # Verifies connection is alive before every request (prevents stale connections)
    "pool_recycle": 280,         # Recycles connections before they time out (Render DB limit ~300s)
    "pool_size": 10,             # Maintains a healthy pool of ready connections
    "max_overflow": 20,          # Allows for bursts without dropping requests
    "pool_timeout": 15,          # Max seconds to wait for connection from pool
    "echo": False,               # Disable SQL logging for performance
    "connect_args": {
        "sslmode": "require",    # Forces secure SSL connection
        "keepalives": 1,         # Enables TCP keepalives
        "keepalives_idle": 30,   # Seconds before sending keepalive probe
        "keepalives_interval": 10,  # Seconds between keepalive probes
        "keepalives_count": 5,   # Max keepalive probes before declaring connection dead
    }
}

# Legacy alias for backwards compatibility
AUTO_SCALING_ENGINE_OPTIONS = SQLALCHEMY_ENGINE_OPTIONS

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

