"""
Single Source of Truth Configuration Factory
Required flags ensure app refuses to start if critical config is missing
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ConfigLevel(Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    DEVELOPMENT_ONLY = "development_only"


class ConfigValidationError(Exception):
    """Raised when required configuration is missing or invalid"""

    pass


@dataclass
class ConfigItem:
    key: str
    level: ConfigLevel
    default: Any = None
    validator: Optional[callable] = None
    description: str = ""


class ConfigFactory:
    """Single source of truth for all configuration"""

    CONFIG_SCHEMA = [
        # Critical - App won't start without these
        ConfigItem(
            "SECRET_KEY",
            ConfigLevel.REQUIRED,
            validator=lambda x: len(x) >= 32,
            description="Flask secret key (min 32 chars)",
        ),
        ConfigItem(
            "SHOPIFY_API_KEY",
            ConfigLevel.REQUIRED,
            validator=lambda x: len(x) >= 20,
            description="Shopify Partners API key",
        ),
        ConfigItem(
            "SHOPIFY_API_SECRET",
            ConfigLevel.REQUIRED,
            validator=lambda x: len(x) >= 30,
            description="Shopify Partners API secret",
        ),
        ConfigItem(
            "DATABASE_URL",
            ConfigLevel.REQUIRED,
            validator=lambda x: x.startswith(("postgresql://", "sqlite://")),
            description="Database connection URL",
        ),
        ConfigItem(
            "ENCRYPTION_KEY",
            ConfigLevel.REQUIRED,
            validator=lambda x: len(x) >= 32,
            description="Data encryption key (min 32 chars)",
        ),
        # Important but has defaults
        ConfigItem("ENVIRONMENT", ConfigLevel.OPTIONAL, "development"),
        ConfigItem("APP_URL", ConfigLevel.OPTIONAL, "http://localhost:5000"),
        ConfigItem("SHOPIFY_API_VERSION", ConfigLevel.OPTIONAL, "2025-10"),
        ConfigItem("LOG_LEVEL", ConfigLevel.OPTIONAL, "INFO"),
        ConfigItem("WTF_CSRF_ENABLED", ConfigLevel.OPTIONAL, True),
        ConfigItem("WTF_CSRF_TIME_LIMIT", ConfigLevel.OPTIONAL, 3600),
        ConfigItem("SQLALCHEMY_TRACK_MODIFICATIONS", ConfigLevel.OPTIONAL, False),
        ConfigItem("MAX_CONTENT_LENGTH", ConfigLevel.OPTIONAL, 16 * 1024 * 1024),
        # Development only
        ConfigItem("DEBUG", ConfigLevel.DEVELOPMENT_ONLY, "False"),
        ConfigItem("TESTING", ConfigLevel.DEVELOPMENT_ONLY, "False"),
    ]

    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.validation_errors: List[str] = []
        self.warnings: List[str] = []

    def load_and_validate(self) -> Dict[str, Any]:
        """Load all configuration and validate strictly"""
        logger = logging.getLogger(__name__)

        environment = os.getenv("ENVIRONMENT", "development")

        for item in self.CONFIG_SCHEMA:
            try:
                self._process_config_item(item, environment)
            except Exception as e:
                if item.level == ConfigLevel.REQUIRED:
                    self.validation_errors.append(f"{item.key}: {str(e)}")
                else:
                    self.warnings.append(f"{item.key}: {str(e)}")

        # Setup derived values
        self._setup_derived_values()

        # Log warnings
        for warning in self.warnings:
            logger.warning(f"Config warning: {warning}")

        # Fail fast on errors
        if self.validation_errors:
            error_msg = "CRITICAL CONFIGURATION ERRORS:\n" + "\n".join(
                f"  - {error}" for error in self.validation_errors
            )
            logger.error(error_msg)
            raise ConfigValidationError(error_msg)

        logger.info(f"✅ Configuration validated successfully for {environment}")
        return self.config

    def _process_config_item(self, item: ConfigItem, environment: str):
        """Process a single configuration item"""
        # Skip development-only items in production
        if item.level == ConfigLevel.DEVELOPMENT_ONLY and environment == "production":
            return

        # Get value from environment
        value = os.getenv(item.key)

        # Handle missing values
        if value is None:
            if item.level == ConfigLevel.REQUIRED:
                raise ValueError(
                    f"Required environment variable not set. {item.description}"
                )
            else:
                value = item.default

        # Clean string values
        if isinstance(value, str):
            value = value.strip().strip('"').strip("'")

        # Convert boolean strings
        if isinstance(value, str) and value.lower() in ("true", "false"):
            value = value.lower() == "true"

        # Validate if validator provided
        if item.validator and value is not None:
            try:
                if not item.validator(value):
                    raise ValueError(f"Validation failed. {item.description}")
            except Exception as e:
                raise ValueError(f"Validation error: {str(e)}. {item.description}")

        self.config[item.key] = value

    def _setup_derived_values(self):
        """Setup values derived from other configuration"""
        # Setup redirect URI
        app_url = self.config.get("APP_URL", "http://localhost:5000")
        self.config["REDIRECT_URI"] = f"{app_url.rstrip('/')}/auth/callback"

        # Setup database URI
        database_url = self.config.get("DATABASE_URL", "sqlite:///app.db")
        self.config["SQLALCHEMY_DATABASE_URI"] = database_url

        # Setup SQLAlchemy engine options
        if "postgresql" in database_url.lower():
            self.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                "pool_size": 10,
                "max_overflow": 20,
                "pool_recycle": 3600,
                "pool_timeout": 30,
                "pool_pre_ping": True,
            }
        else:
            self.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}


# Global config instance
_config_factory = ConfigFactory()
_config_cache = None


def get_config() -> Dict[str, Any]:
    """Get validated configuration (cached after first load)"""
    global _config_cache
    if _config_cache is None:
        _config_cache = _config_factory.load_and_validate()
    return _config_cache


def require_config(key: str) -> Any:
    """Get required config value, fail fast if missing"""
    config = get_config()
    if key not in config:
        raise ConfigValidationError(f"Required config key '{key}' not found")
    return config[key]


def get_config_safe(key: str, default: Any = None) -> Any:
    """Get config value with safe fallback"""
    try:
        return get_config().get(key, default)
    except ConfigValidationError:
        return default


# Backward compatibility exports
SHOPIFY_API_VERSION = get_config_safe("SHOPIFY_API_VERSION", "2025-10")


# Auto-scaling database configuration
AUTO_SCALING_ENGINE_OPTIONS = {
    "pool_size": 20,  # Start with 20 connections
    "max_overflow": 50,  # Can burst to 70 total connections
    "pool_recycle": 3600,  # Recycle connections every hour
    "pool_timeout": 30,  # 30 second timeout
    "pool_pre_ping": True,  # Verify connections before use
    "echo": False,  # Disable SQL logging in production
}

# Connection pooling for high-traffic
if os.getenv("ENVIRONMENT") == "production":
    AUTO_SCALING_ENGINE_OPTIONS.update(
        {
            "pool_size": 50,  # Higher pool for production
            "max_overflow": 100,  # Can handle 150 concurrent connections
            "pool_recycle": 1800,  # Recycle every 30 minutes
        }
    )

# Redis configuration for session storage (scales to millions of users)
AUTO_SCALING_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
AUTO_SCALING_SESSION_TYPE = "redis" if AUTO_SCALING_REDIS_URL else "filesystem"
AUTO_SCALING_SESSION_REDIS = AUTO_SCALING_REDIS_URL if AUTO_SCALING_REDIS_URL else None
AUTO_SCALING_SESSION_PERMANENT = False
AUTO_SCALING_SESSION_USE_SIGNER = True
AUTO_SCALING_SESSION_KEY_PREFIX = "employeesuite:"

# Backward compatibility exports
try:
    config = get_config()
    DEBUG_MODE = config.get("DEBUG", False)
    ENCRYPTION_KEY = config.get("ENCRYPTION_KEY", "")
    SHOPIFY_API_VERSION = config.get("SHOPIFY_API_VERSION", "2025-10")
except:
    # Fallback values
    DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")
    SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2025-10")
