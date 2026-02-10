from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, event, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.types import BigInteger, Boolean, DateTime, Integer, String
from werkzeug.security import check_password_hash, generate_password_hash

from config import config

db = SQLAlchemy()
logger = logging.getLogger(__name__)


class TimestampMixin:
    """Mixin for adding timestamp fields to models"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class User(UserMixin, db.Model, TimestampMixin):
    """User model with proper type hints and validation"""

    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # User credentials
    email: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Trial and subscription
    trial_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(days=7),
        nullable=False,
    )
    is_subscribed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Stripe integration
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )

    # Password reset
    reset_token: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # User preferences
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    shopify_stores: Mapped[List["ShopifyStore"]] = relationship(
        "ShopifyStore",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_user_email_active", "email", "is_active"),
        Index("idx_user_subscription", "is_subscribed", "trial_ends_at"),
        Index("idx_user_stripe", "stripe_customer_id"),
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize user with validation"""
        super().__init__(**kwargs)

    @validates("email")
    def validate_email(self, key: str, email: str) -> str:
        """Validate email format"""
        if not email or "@" not in email:
            raise ValueError("Valid email address is required")
        return email.lower().strip()

    @validates("password_hash")
    def validate_password_hash(self, key: str, password_hash: str) -> str:
        """Validate password hash"""
        if not password_hash:
            raise ValueError("Password hash cannot be empty")
        return password_hash

    def set_password(self, password: str) -> None:
        """Set password with proper hashing"""
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check password against hash"""
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)

    def is_trial_active(self) -> bool:
        """Check if user's trial is still active"""
        if self.is_subscribed:
            return False
            
        if not self.trial_started_at or not self.trial_ends_at:
            return False

        now = datetime.now(timezone.utc)
        
        # Ensure trial_ends_at is timezone-aware
        if self.trial_ends_at.tzinfo is None:
            trial_end = self.trial_ends_at.replace(tzinfo=timezone.utc)
        else:
            trial_end = self.trial_ends_at
        
        return now < trial_end

    # Static cache for has_access results (User ID -> (status, expiry))
    _access_cache = {}

    def has_access(self) -> bool:
        """Check if user has access (subscribed or trial active) - with 10-minute cache"""
        import time
        now = time.time()
        
        # Check class-level cache to avoid DB hit (10 min = 600s)
        if hasattr(self, 'id') and self.id in User._access_cache:
            cached_val, expiry = User._access_cache[self.id]
            if now < expiry:
                return cached_val
                
        # Fresh check if not in cache or expired
        try:
            from config import DEV_SHOP_DOMAIN, ADMIN_EMAIL
            
            # 1. BILLING BYPASS: Check if this is our development shop or admin user
            is_admin = hasattr(self, 'email') and self.email == ADMIN_EMAIL
            is_dev_shop = hasattr(self, 'active_shop') and self.active_shop == DEV_SHOP_DOMAIN
            
            if is_admin or is_dev_shop:
                logger.info(f"🚀 Billing bypass active for {'admin' if is_admin else 'dev shop'}: {getattr(self, 'email', 'unknown') if is_admin else self.active_shop}")
                return True

            # 2. STANDARD CHECK: Subscribed or Trial Active
            # 10k GHOST SHIP: Be optimistic. If we can't reach DB, use last known status.
            access_status = self.is_subscribed or self.is_trial_active()
        except Exception as e:
            logger.error(f"Error checking access status for user {getattr(self, 'id', 'unknown')}: {e}")
            # If DB is down, assume True if they were previously OK, or False if new
            return False
        
        # Store in cache
        if hasattr(self, 'id'):
            User._access_cache[self.id] = (access_status, now + 600)
            
        return access_status

    def get_trial_days_left(self) -> int:
        """Get number of trial days remaining"""
        if not self.trial_ends_at or self.is_subscribed:
            return 0

        now = datetime.now(timezone.utc)
        
        # Ensure timezone consistency
        if self.trial_ends_at.tzinfo is None:
            trial_end = self.trial_ends_at.replace(tzinfo=timezone.utc)
        else:
            trial_end = self.trial_ends_at
        
        if now >= trial_end:
            return 0

        # Use ceiling to be generous with partial days
        import math
        delta = trial_end - now
        return math.ceil(delta.total_seconds() / 86400)  # 86400 seconds in a day

    def update_last_login(self) -> None:
        """Update last login timestamp"""
        self.last_login = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary (safe for JSON)"""
        return {
            "id": self.id,
            "email": self.email,
            "is_subscribed": self.is_subscribed,
            "trial_active": self.is_trial_active(),
            "trial_days_left": self.get_trial_days_left(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

    @classmethod
    def expire_trials(cls):
        """Expire trials that have ended - call this from a cron job"""
        now = datetime.now(timezone.utc)
        expired_users = cls.query.filter(
            cls.trial_ends_at < now,
            cls.is_subscribed == False
        ).all()
        
        for user in expired_users:
            logger.info(f"Trial expired for user {user.email}")
            # Could send expiration email here
        
        return len(expired_users)

    @property
    def shop_domain(self) -> Optional[str]:
        """Convenience property for primary shop domain (myshopify.com URL)"""
        # Look for active store first
        store = self.shopify_stores.filter_by(is_active=True).first()
        if not store:
            # Fallback to any store if none active
            store = self.shopify_stores.first()
        return store.shop_url if store else None

    @property
    def active_shop(self) -> Optional[str]:
        """Returns the shop_url of the current ACTIVE store connection (with Dev Safe-Pass)"""
        from config import DEV_SHOP_DOMAIN
        store = self.shopify_stores.filter_by(is_active=True).first()
        
        # Dev Safe-Pass: If no active store but this is our dev shop, return any store record
        if not store and DEV_SHOP_DOMAIN:
            dev_store = self.shopify_stores.filter_by(shop_url=DEV_SHOP_DOMAIN).first()
            if dev_store:
                return dev_store.shop_url
                
        return store.shop_url if store else None

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class ShopifyStore(db.Model, TimestampMixin):
    """Shopify store model with proper type hints and validation"""

    __tablename__ = "shopify_stores"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Foreign key to user
    user_id: Mapped[int] = mapped_column(
        Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Store information
    shop_url: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    shop_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, index=True
    )
    shop_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Access token (encrypted)
    access_token: Mapped[str] = mapped_column(String(500), nullable=False)

    # Billing information
    charge_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    billing_plan: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Store status
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    is_installed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    uninstalled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Shopify app permissions
    scopes_granted: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Store metadata
    shop_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shop_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shop_timezone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    shop_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="shopify_stores")

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("idx_store_shop_active", "shop_url", "is_active"),
        Index("idx_store_user_active", "user_id", "is_active"),
        Index("idx_store_shop_id", "shop_id"),
        Index("idx_store_charge", "charge_id"),
        db.UniqueConstraint("shop_url", name="uq_shop_url"),
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize store with validation"""
        # Auto-parse shop_id if provided as GID
        if "shop_id" in kwargs and isinstance(kwargs["shop_id"], str):
            try:
                from shopify_utils import parse_gid

                kwargs["shop_id"] = parse_gid(kwargs["shop_id"])
            except (ImportError, ValueError) as e:
                logger.warning(f"Could not parse shop_id GID: {e}")

        super().__init__(**kwargs)

    @validates("shop_url")
    def validate_shop_url(self, key: str, shop_url: str) -> str:
        """Validate and normalize shop URL"""
        from shopify_utils import normalize_shop_url

        return normalize_shop_url(shop_url)

    @validates("access_token")
    def validate_access_token(self, key: str, token: str) -> str:
        """Validate access token"""
        if not token:
            raise ValueError("Access token cannot be empty")

        # Validate token format (Shopify tokens start with shpat_ or shpca_)
        if not (
            token.startswith("shpat_") or token.startswith("shpca_") or len(token) > 40
        ):
            # Might be encrypted, allow it
            pass

        return token

    @validates("scopes_granted")
    def validate_scopes(self, key: str, scopes: Optional[str]) -> Optional[str]:
        """Validate granted scopes"""
        if not scopes:
            return scopes

        # Basic validation - scopes should be comma-separated
        if "," in scopes:
            # Clean up scopes
            scope_list = [s.strip() for s in scopes.split(",") if s.strip()]
            return ",".join(scope_list)

        return scopes.strip()

    def disconnect(self) -> None:
        """Disconnect store - marks as inactive and clears sensitive data"""
        self.is_active = False
        self.is_installed = False
        self.uninstalled_at = datetime.now(timezone.utc)
        self.charge_id = None
        # Note: We keep access_token for potential reconnection

        logger.info(f"Store {self.shop_url} disconnected for user {self.user_id}")

    def reconnect(self, new_access_token: str) -> None:
        """Reconnect store with new access token"""
        self.access_token = new_access_token
        self.is_active = True
        self.is_installed = True
        self.uninstalled_at = None

        logger.info(f"Store {self.shop_url} reconnected for user {self.user_id}")

    def is_connected(self) -> bool:
        """Check if store is properly connected"""
        return (
            self.is_active
            and self.is_installed
            and bool(self.access_token)
            and self.uninstalled_at is None
        )

    def get_access_token(self) -> Optional[str]:
        """Get decrypted access token with graceful failure handling"""
        if not self.access_token:
            return None

        try:
            from data_encryption import decrypt_access_token

            decrypted = decrypt_access_token(self.access_token)

            if decrypted is None:
                # Decryption failed - token is invalid/corrupted
                logger.warning(
                    f"Access token decryption failed for store {self.shop_url}"
                )
                # Mark store as needing reconnection
                self.is_active = False
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                return None

            return decrypted

        except Exception as e:
            logger.error(
                f"Access token retrieval failed for store {self.shop_url}: {e}"
            )
            return None

    def set_access_token(self, token: str) -> None:
        """Set access token with encryption if enabled"""
        if not token:
            raise ValueError("Access token cannot be empty")

        # Try to encrypt token if encryption is available
        try:
            from data_encryption import encrypt_access_token

            encrypted = encrypt_access_token(token)

            if encrypted:
                self.access_token = encrypted
                logger.debug(f"Access token encrypted for store {self.shop_url}")
            else:
                # Encryption failed or not available, store plaintext
                self.access_token = token
                logger.warning(
                    f"Storing plaintext access token for store {self.shop_url}"
                )

        except Exception as e:
            logger.warning(f"Encryption failed for store {self.shop_url}: {e}")
            self.access_token = token

    def update_shop_info(self, shop_data: Dict[str, Any]) -> None:
        """Update shop information from Shopify API response"""
        if "id" in shop_data:
            self.shop_id = shop_data["id"]

        if "name" in shop_data:
            self.shop_name = shop_data["name"]

        if "domain" in shop_data:
            self.shop_domain = shop_data["domain"]

        if "email" in shop_data:
            self.shop_email = shop_data["email"]

        if "iana_timezone" in shop_data:
            self.shop_timezone = shop_data["iana_timezone"]

        if "currency" in shop_data:
            self.shop_currency = shop_data["currency"]

    def to_dict(self) -> Dict[str, Any]:
        """Convert store to dictionary (safe for JSON)"""
        return {
            "id": self.id,
            "shop_url": self.shop_url,
            "shop_id": self.shop_id,
            "shop_name": self.shop_name,
            "shop_domain": self.shop_domain,
            "is_active": self.is_active,
            "is_connected": self.is_connected(),
            "billing_plan": self.billing_plan,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<ShopifyStore {self.shop_url}>"


# Event listeners for automatic timestamp updates
@event.listens_for(User, "before_update")
@event.listens_for(ShopifyStore, "before_update")
def update_timestamp(mapper, connection, target):
    """Automatically update timestamp on record update"""
    target.updated_at = datetime.now(timezone.utc)


# Database initialization and migration helpers
def init_db(app):
    """Initialize database with error handling"""
    with app.app_context():
        try:
            # Test connection first
            db.session.execute(db.text("SELECT 1"))
            logger.info("Database connection verified")

            # Create tables if they don't exist
            db.create_all()
            logger.info("Database tables created/verified")

            # Run any pending migrations
            try:
                from migrations import run_migrations

                run_migrations(app)
            except ImportError:
                logger.info("No migrations module found")
            except Exception as e:
                logger.warning(f"Migration warning: {e}")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            # Don't raise in production - let app start with limited functionality
            if os.getenv("ENVIRONMENT") == "production":
                logger.warning("Continuing with database issues in production")
            else:
                raise


def _add_column(table: str, column: str, col_type: str) -> None:
    """Add a column to a table if it doesn't exist. Each call uses its own transaction."""
    try:
        inspector = db.inspect(db.engine)
        existing = [col["name"] for col in inspector.get_columns(table)]
        if column in existing:
            return
        db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        db.session.commit()
        logger.info(f"Added {column} column to {table} table")
    except Exception as e:
        db.session.rollback()
        error_str = str(e).lower()
        if "already exists" in error_str or "duplicate" in error_str:
            logger.debug(f"Column {column} already exists on {table}")
        else:
            logger.error(f"Failed to add {column} to {table}: {e}")


def run_migrations(app) -> None:
    """Run database migrations"""
    with app.app_context():
        try:
            # Users table migrations
            _add_column("users", "trial_started_at", "TIMESTAMP")
            _add_column("users", "email_verified", "BOOLEAN DEFAULT FALSE")
            _add_column("users", "is_active", "BOOLEAN DEFAULT TRUE")
            _add_column("users", "last_login", "TIMESTAMP")
            _add_column("users", "reset_token", "VARCHAR(100)")
            _add_column("users", "reset_token_expires", "TIMESTAMP")

            # ShopifyStore table migrations
            _add_column("shopify_stores", "shop_name", "VARCHAR(255)")
            _add_column("shopify_stores", "shop_id", "BIGINT")
            _add_column("shopify_stores", "charge_id", "VARCHAR(255)")
            _add_column("shopify_stores", "uninstalled_at", "TIMESTAMP")
            _add_column("shopify_stores", "shop_domain", "VARCHAR(255)")
            _add_column("shopify_stores", "shop_email", "VARCHAR(255)")
            _add_column("shopify_stores", "shop_timezone", "VARCHAR(255)")
            _add_column("shopify_stores", "shop_currency", "VARCHAR(255)")
            _add_column("shopify_stores", "billing_plan", "VARCHAR(255)")
            _add_column("shopify_stores", "scopes_granted", "VARCHAR(500)")
            _add_column("shopify_stores", "is_installed", "BOOLEAN DEFAULT TRUE")

        except Exception as e:
            logger.error(f"Migration failed: {e}")


# Utility functions
def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email address"""
    return User.query.filter_by(email=email.lower().strip(), is_active=True).first()


def get_store_by_shop_url(
    shop_url: str, user_id: Optional[int] = None
) -> Optional[ShopifyStore]:
    """Get store by shop URL"""
    query = ShopifyStore.query.filter_by(
        shop_url=shop_url.lower().strip(), is_active=True
    )

    if user_id:
        query = query.filter_by(user_id=user_id)

    return query.first()


def create_user(email: str, password: str) -> User:
    """Create new user with validation"""
    existing_user = get_user_by_email(email)
    if existing_user:
        raise ValueError("User with this email already exists")

    user = User(email=email)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    logger.info(f"Created new user: {email}")
    return user


def create_shopify_store(
    user_id: int, shop_url: str, access_token: str, **kwargs
) -> ShopifyStore:
    """Create new Shopify store connection"""
    # Check if store already exists
    existing_store = get_store_by_shop_url(shop_url, user_id)
    if existing_store:
        # Reactivate existing store
        existing_store.reconnect(access_token)
        db.session.commit()
        return existing_store

    store = ShopifyStore(user_id=user_id, shop_url=shop_url, **kwargs)
    store.set_access_token(access_token)

    db.session.add(store)
    db.session.commit()

    logger.info(f"Created new store connection: {shop_url} for user {user_id}")
    return store


# ============================================================================
# ENHANCED MODELS (Merged from enhanced_models.py)
# ============================================================================

# Subscription Plan Types
PLAN_FREE = 'free'
PLAN_PRO = 'pro'
PLAN_MANUAL = 'manual'
PLAN_AUTOMATED = 'automated'

# Plan Pricing (Updated for Production: $39/month single plan)
PLAN_PRICES = {
    PLAN_FREE: 0.00,
    PLAN_PRO: 39.00,
}

# Plan Features
PLAN_FEATURES = {
    PLAN_FREE: {
        'name': 'Free Trial',
        'price': 0,
        'stores_limit': 1,
        'data_days': 7,
        'csv_exports': False,
        'auto_download': False,
        'scheduled_reports': False,
        'email_reports': False,
        'sms_reports': False,
        'priority_support': False,
        'api_access': False,
    },
    PLAN_PRO: {
        'name': 'Employee Suite Pro',
        'price': 39,
        'stores_limit': -1,  # Unlimited stores
        'data_days': -1,    # Unlimited historical data
        'csv_exports': True,
        'auto_download': True,
        'scheduled_reports': True,
        'email_reports': True,
        'sms_reports': True,
        'priority_support': True,
        'api_access': True,
    },
}

class UserSettings(db.Model):
    """User preferences and settings"""
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True)
    
    # Auto-download settings
    auto_download_orders = db.Column(db.Boolean, default=False)
    auto_download_inventory = db.Column(db.Boolean, default=False)
    auto_download_revenue = db.Column(db.Boolean, default=False)
    
    # Scheduled reports
    scheduled_reports_enabled = db.Column(db.Boolean, default=False)
    report_frequency = db.Column(db.String(20), default='daily')  # daily, weekly, monthly
    report_time = db.Column(db.String(10), default='09:00')  # HH:MM format
    report_timezone = db.Column(db.String(50), default='UTC')
    report_delivery_email = db.Column(db.String(120), nullable=True)
    report_delivery_sms = db.Column(db.String(20), nullable=True)  # Phone number
    
    # Date range preferences
    default_date_range_days = db.Column(db.Integer, default=30)  # Default to last 30 days
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='settings', uselist=False)
    
    def __repr__(self):
        return f'<UserSettings user_id={self.user_id}>'

class SubscriptionPlan(db.Model):
    """Subscription plan details"""
    __tablename__ = 'subscription_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    plan_type = db.Column(db.String(20), nullable=False)  # 'manual' or 'automated'
    price_usd = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Plan features (focused on single store automation)
    automated_reports_enabled = db.Column(db.Boolean, default=True)
    scheduled_delivery_enabled = db.Column(db.Boolean, default=True)
    csv_exports_enabled = db.Column(db.Boolean, default=True)
    priority_support_enabled = db.Column(db.Boolean, default=True)
    
    # Shopify billing
    charge_id = db.Column(db.String(255), nullable=True, index=True)
    status = db.Column(db.String(20), default='active')  # active, cancelled, expired
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship('User', backref='subscription_plan')
    
    def __repr__(self):
        return f'<SubscriptionPlan user_id={self.user_id} plan={self.plan_type}>'

class ScheduledReport(db.Model):
    """Scheduled report delivery"""
    __tablename__ = 'scheduled_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    report_type = db.Column(db.String(20), nullable=False)  # 'orders', 'inventory', 'revenue', 'all'
    frequency = db.Column(db.String(20), default='daily')
    delivery_time = db.Column(db.String(10), default='09:00')
    timezone = db.Column(db.String(50), default='UTC')
    
    # Delivery method
    delivery_email = db.Column(db.String(120), nullable=True)
    delivery_sms = db.Column(db.String(20), nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)  # Added index for composite queries
    last_sent_at = db.Column(db.DateTime, nullable=True, index=True)  # Added index for queries
    next_send_at = db.Column(db.DateTime, nullable=True, index=True)  # Added index for queries
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='scheduled_reports')
    
    # Composite index for common query pattern: filter_by(user_id=user_id, is_active=True)
    __table_args__ = (
        db.Index('idx_scheduled_report_user_active', 'user_id', 'is_active'),
    )
    
    def calculate_next_send(self):
        """Calculate next send time based on frequency"""
        now = datetime.utcnow()
        time_parts = self.delivery_time.split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        
        if self.frequency == 'daily':
            next_send = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_send <= now:
                next_send += timedelta(days=1)
        elif self.frequency == 'weekly':
            days_ahead = 7 - now.weekday()
            next_send = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
        elif self.frequency == 'monthly':
            next_send = now.replace(day=1, hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=32)
            next_send = next_send.replace(day=1)
        else:
            next_send = now + timedelta(days=1)
        
        return next_send
    
    def __repr__(self):
        return f'<ScheduledReport user_id={self.user_id} type={self.report_type}>'

# Extend User model with helper methods
def get_user_plan(user):
    """Get user's subscription plan"""
    plan = SubscriptionPlan.query.filter_by(user_id=user.id, status='active').first()
    return plan

def get_user_plan_type(user):
    """Get user's plan type string, defaults to FREE"""
    plan = get_user_plan(user)
    if plan:
        return plan.plan_type
    return PLAN_FREE

def get_plan_features(user):
    """Get features dict for user's plan"""
    if user.is_subscribed:
        return PLAN_FEATURES[PLAN_PRO]
    elif user.is_trial_active():
        return PLAN_FEATURES[PLAN_PRO]  # Trial gets Pro features
    else:
        return PLAN_FEATURES[PLAN_FREE]  # Expired trial gets no features

def get_user_settings(user):
    """Get or create user settings"""
    settings = UserSettings.query.filter_by(user_id=user.id).first()
    if not settings:
        settings = UserSettings(user_id=user.id)
        db.session.add(settings)
        db.session.commit()
    return settings

def is_automated_plan(user):
    """Check if user has automated plan features (Pro plan)"""
    return user.is_subscribed

def is_pro_or_higher(user):
    """Check if user has Pro plan"""
    return user.is_subscribed

def can_export_csv(user):
    """Check if user can export CSV files"""
    features = get_plan_features(user)
    return features.get('csv_exports', False)

def can_auto_download(user):
    """Check if user can use auto-download"""
    features = get_plan_features(user)
    return features.get('auto_download', False)

def can_scheduled_reports(user):
    """Check if user can use scheduled reports"""
    features = get_plan_features(user)
    return features.get('scheduled_reports', False)

def can_email_reports(user):
    """Check if user can use email reports"""
    features = get_plan_features(user)
    return features.get('email_reports', False)

def can_sms_reports(user):
    """Check if user can use SMS reports"""
    features = get_plan_features(user)
    return features.get('sms_reports', False)

def can_multi_store(user):
    """Check if user can connect multiple stores"""
    features = get_plan_features(user)
    stores_limit = features.get('stores_limit', 1)
    return stores_limit == -1 or stores_limit > 1

def get_stores_limit(user):
    """Get max stores allowed for user's plan"""
    features = get_plan_features(user)
    return features.get('stores_limit', 1)

def get_data_days_limit(user):
    """Get max data history days for user's plan"""
    features = get_plan_features(user)
    return features.get('data_days', 7)
