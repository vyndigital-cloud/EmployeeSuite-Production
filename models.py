from __future__ import annotations

import logging
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
        if not self.trial_ends_at:
            return False

        # FIX: Handle timezone-aware vs timezone-naive datetime comparison
        now = datetime.now(timezone.utc)

        # Make trial_ends_at timezone-aware if it's naive
        if self.trial_ends_at.tzinfo is None:
            trial_end = self.trial_ends_at.replace(tzinfo=timezone.utc)
        else:
            trial_end = self.trial_ends_at

        return now < trial_end and not self.is_subscribed

    def has_access(self) -> bool:
        """Check if user has access (subscribed or trial active)"""
        return self.is_subscribed or self.is_trial_active()

    def get_trial_days_left(self) -> int:
        """Get number of trial days remaining"""
        if not self.trial_ends_at or self.is_subscribed:
            return 0

        now = datetime.now(timezone.utc)
        if now >= self.trial_ends_at:
            return 0

        return (self.trial_ends_at - now).days

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
        from utils import normalize_shop_url

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
def init_db(app) -> None:
    """Initialize database with application context.

    Note: db.init_app(app) must be called before this function.
    This only creates tables and runs migrations.
    """
    # Create all tables
    db.create_all()

    # Run any necessary migrations
    run_migrations(app)

    logger.info("Database initialized successfully")


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
    """Run database migrations - each column addition is independent."""
    try:
        with app.app_context():
            # Users table migrations
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
