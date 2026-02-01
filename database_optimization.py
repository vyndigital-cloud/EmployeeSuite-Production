"""
Enterprise Database Optimization
Implements connection pooling, query optimization, and monitoring
"""

import logging
import os

from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


def create_enterprise_engine():
    """Create enterprise-grade database engine with optimizations"""
    database_url = os.getenv("DATABASE_URL")

    # Enterprise connection pool configuration
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=50,  # Increased for enterprise load
        max_overflow=100,  # Handle traffic spikes
        pool_recycle=3600,  # 1 hour
        pool_timeout=30,
        pool_pre_ping=True,
        echo=False,  # Disable in production
        connect_args={
            "connect_timeout": 10,
            "application_name": "EmployeeSuite_Production",
            "options": "-c statement_timeout=30000",  # 30 second query timeout
        },
    )

    # Add connection monitoring
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if "postgresql" in database_url:
            with dbapi_connection.cursor() as cursor:
                # Optimize PostgreSQL settings
                cursor.execute("SET work_mem = '256MB'")
                cursor.execute("SET maintenance_work_mem = '512MB'")
                cursor.execute("SET effective_cache_size = '4GB'")

    return engine


# Database indexes for enterprise performance
ENTERPRISE_INDEXES = [
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_active ON users(email, is_active) WHERE is_active = true",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_subscription_trial ON users(is_subscribed, trial_ends_at) WHERE is_subscribed = false",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stores_shop_url_active ON shopify_stores(shop_url, is_active) WHERE is_active = true",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stores_user_active ON shopify_stores(user_id, is_active) WHERE is_active = true",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stores_created_at ON shopify_stores(created_at DESC)",
]


def create_enterprise_indexes(db):
    """Create enterprise-grade database indexes"""
    for index_sql in ENTERPRISE_INDEXES:
        try:
            db.session.execute(text(index_sql))
            db.session.commit()
            logger.info(f"Created index: {index_sql[:50]}...")
        except Exception as e:
            db.session.rollback()
            if "already exists" not in str(e).lower():
                logger.warning(f"Index creation failed: {e}")
