import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class Config:
    """Application configuration with validation"""

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    TESTING: bool = os.getenv("TESTING", "False").lower() == "true"

    # Flask Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    WTF_CSRF_ENABLED: bool = True
    WTF_CSRF_TIME_LIMIT: int = 3600  # 1 hour

    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_DATABASE_URI: str = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: Dict[str, Any] = None

    # Shopify Configuration
    SHOPIFY_API_KEY: str = os.getenv("SHOPIFY_API_KEY", "")
    SHOPIFY_API_SECRET: str = os.getenv("SHOPIFY_API_SECRET", "")
    SHOPIFY_API_VERSION: str = os.getenv("SHOPIFY_API_VERSION", "2025-10")
    SHOPIFY_SCOPES: str = os.getenv(
        "SHOPIFY_SCOPES",
        "read_products,write_products,read_orders,write_orders,read_inventory,write_inventory",
    )

    # App URLs
    APP_URL: str = os.getenv("APP_URL", "http://localhost:5000")
    REDIRECT_URI: str = ""  # Will be set based on APP_URL

    # Security & Encryption
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ACCESS_TOKEN_EXPIRES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "86400")
    )  # 24 hours

    # Stripe Configuration
    STRIPE_PUBLIC_KEY: str = os.getenv("STRIPE_PUBLIC_KEY", "")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # SendGrid Configuration
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "noreply@example.com")

    # Sentry Configuration
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    SENTRY_ENVIRONMENT: str = os.getenv("SENTRY_ENVIRONMENT", ENVIRONMENT)

    # Rate Limiting
    RATELIMIT_STORAGE_URL: str = os.getenv("RATELIMIT_STORAGE_URL", "memory://")
    RATELIMIT_DEFAULT: str = os.getenv("RATELIMIT_DEFAULT", "100 per hour")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Performance
    CACHE_TYPE: str = os.getenv("CACHE_TYPE", "simple")
    CACHE_REDIS_URL: str = os.getenv("CACHE_REDIS_URL", "")
    CACHE_DEFAULT_TIMEOUT: int = int(
        os.getenv("CACHE_DEFAULT_TIMEOUT", "300")
    )  # 5 minutes

    # File Upload
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "uploads")

    def __post_init__(self):
        """Validate configuration after initialization"""
        self.validate()
        self.setup_derived_values()

    def validate(self) -> None:
        """Validate critical configuration values"""
        errors = []
        warnings = []

        # Critical validations for production
        if self.ENVIRONMENT == "production":
            if not self.SECRET_KEY:
                errors.append("SECRET_KEY must be set in production")
            elif len(self.SECRET_KEY) < 32:
                errors.append("SECRET_KEY must be at least 32 characters long")

            if not self.ENCRYPTION_KEY:
                errors.append("ENCRYPTION_KEY must be set in production")
            elif len(self.ENCRYPTION_KEY) < 32:
                errors.append("ENCRYPTION_KEY must be at least 32 characters long")

            if not self.SHOPIFY_API_KEY:
                errors.append("SHOPIFY_API_KEY must be set in production")

            if not self.SHOPIFY_API_SECRET:
                errors.append("SHOPIFY_API_SECRET must be set in production")

            if not self.DATABASE_URL or "sqlite" in self.DATABASE_URL.lower():
                errors.append("Production must use PostgreSQL, not SQLite")

            if self.DEBUG:
                warnings.append("DEBUG should be False in production")

        # Development validations
        if self.ENVIRONMENT == "development":
            if not self.SECRET_KEY:
                object.__setattr__(
                    self, "SECRET_KEY", "dev-secret-key-change-in-production"
                )
                warnings.append("Using default SECRET_KEY for development")

            if not self.ENCRYPTION_KEY:
                import secrets

                object.__setattr__(self, "ENCRYPTION_KEY", secrets.token_urlsafe(32))
                warnings.append("Generated temporary ENCRYPTION_KEY for development")

        # General validations
        if not self.APP_URL:
            errors.append("APP_URL must be set")

        if self.APP_URL and not (
            self.APP_URL.startswith("http://") or self.APP_URL.startswith("https://")
        ):
            errors.append("APP_URL must start with http:// or https://")

        if self.ENVIRONMENT == "production" and self.APP_URL.startswith("http://"):
            warnings.append("Production should use HTTPS (https://)")

        # Log errors and warnings
        logger = logging.getLogger(__name__)
        for warning in warnings:
            logger.warning(f"Configuration warning: {warning}")

        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

    def setup_derived_values(self) -> None:
        """Setup values derived from other configuration"""
        # Setup redirect URI
        if not self.REDIRECT_URI:
            object.__setattr__(
                self, "REDIRECT_URI", f"{self.APP_URL.rstrip('/')}/auth/callback"
            )

        # Setup SQLAlchemy engine options
        if not self.SQLALCHEMY_ENGINE_OPTIONS:
            if "postgresql" in self.DATABASE_URL.lower():
                object.__setattr__(
                    self,
                    "SQLALCHEMY_ENGINE_OPTIONS",
                    {
                        "pool_size": 10,
                        "max_overflow": 20,
                        "pool_recycle": 3600,
                        "pool_timeout": 30,
                        "pool_pre_ping": True,
                    },
                )
            else:
                object.__setattr__(self, "SQLALCHEMY_ENGINE_OPTIONS", {})

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"

    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.TESTING or self.ENVIRONMENT == "testing"

    def get_database_url(self) -> str:
        """Get database URL with proper formatting"""
        return self.DATABASE_URL

    def get_shopify_redirect_uri(self) -> str:
        """Get Shopify OAuth redirect URI"""
        return self.REDIRECT_URI

    def get_log_level(self) -> int:
        """Get numeric log level"""
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        return levels.get(self.LOG_LEVEL.upper(), logging.INFO)


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True  # Log SQL queries in development


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False

    def __post_init__(self):
        super().__post_init__()
        # Additional production validations
        if not self.SENTRY_DSN:
            logging.warning(
                "SENTRY_DSN not set - error tracking disabled in production"
            )


class TestingConfig(Config):
    """Testing configuration"""

    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


# Configuration factory
def get_config() -> Config:
    """Get configuration based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()

    config_map = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }

    config_class = config_map.get(env, DevelopmentConfig)
    return config_class()


# Create global config instance
config = get_config()


def validate_required_env_vars():
    """Validate critical environment variables on startup"""
    if os.getenv("ENVIRONMENT") == "production":
        required = [
            "SECRET_KEY",
            "DATABASE_URL",
            "SHOPIFY_API_KEY",
            "SHOPIFY_API_SECRET",
        ]
        missing = [var for var in required if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required production variables: {missing}")

    # Validate SECRET_KEY length
    secret_key = os.getenv("SECRET_KEY", "")
    if secret_key and len(secret_key) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters long")


# Call validation immediately
validate_required_env_vars()

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
DEBUG_MODE = config.DEBUG
ENCRYPTION_KEY = config.ENCRYPTION_KEY
SHOPIFY_API_VERSION = config.SHOPIFY_API_VERSION
