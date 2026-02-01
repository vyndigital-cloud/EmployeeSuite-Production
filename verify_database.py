#!/usr/bin/env python3
"""
DATABASE VERIFICATION SCRIPT
============================

This script verifies the database schema and checks for common issues.
It's useful for debugging production database problems.

Usage:
python verify_database.py
"""

import logging
import sys
from datetime import datetime

from sqlalchemy import inspect, text

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def verify_database():
    """Verify database schema and data integrity"""
    try:
        # Import the app and database
        from app import app, db

        with app.app_context():
            logger.info("🔍 Starting database verification...")

            # Get database info
            dialect = db.engine.dialect.name
            logger.info(f"Database type: {dialect}")

            # Get database inspector
            inspector = inspect(db.engine)

            # Check if tables exist
            tables = inspector.get_table_names()
            logger.info(f"Available tables: {tables}")

            # Verify users table
            if "users" not in tables:
                logger.error("❌ Users table does not exist!")
                return False

            # Check users table columns
            user_columns = [col["name"] for col in inspector.get_columns("users")]
            logger.info(f"Users table columns: {user_columns}")

            # Required columns for User model
            required_user_columns = [
                "id",
                "email",
                "password_hash",
                "trial_ends_at",
                "is_subscribed",
                "is_active",
                "email_verified",
                "created_at",
                "updated_at",
            ]

            missing_columns = []
            for col in required_user_columns:
                if col not in user_columns:
                    missing_columns.append(col)

            if missing_columns:
                logger.error(f"❌ Missing columns in users table: {missing_columns}")
            else:
                logger.info("✅ All required user columns present")

            # Verify shopify_stores table
            if "shopify_stores" not in tables:
                logger.error("❌ Shopify_stores table does not exist!")
                return False

            store_columns = [
                col["name"] for col in inspector.get_columns("shopify_stores")
            ]
            logger.info(f"Shopify_stores table columns: {store_columns}")

            # Test database connectivity with simple queries
            try:
                # Count users
                result = db.session.execute(text("SELECT COUNT(*) as count FROM users"))
                user_count = result.fetchone()[0]
                logger.info(f"Total users: {user_count}")

                # Count active users (if is_active column exists)
                if "is_active" in user_columns:
                    result = db.session.execute(
                        text(
                            "SELECT COUNT(*) as count FROM users WHERE is_active = TRUE"
                        )
                    )
                    active_count = result.fetchone()[0]
                    logger.info(f"Active users: {active_count}")

                # Count shopify stores
                result = db.session.execute(
                    text("SELECT COUNT(*) as count FROM shopify_stores")
                )
                store_count = result.fetchone()[0]
                logger.info(f"Total Shopify stores: {store_count}")

            except Exception as query_error:
                logger.error(f"❌ Database query failed: {query_error}")
                return False

            # Test if we can import and use the models
            try:
                from models import ShopifyStore, User

                logger.info("✅ Models imported successfully")

                # Test model queries
                users = User.query.limit(1).all()
                stores = ShopifyStore.query.limit(1).all()
                logger.info("✅ Model queries working")

            except Exception as model_error:
                logger.error(f"❌ Model test failed: {model_error}")
                return False

            # Summary
            print("\n" + "=" * 60)
            print("📊 DATABASE VERIFICATION SUMMARY")
            print("=" * 60)
            print(f"Database Type: {dialect}")
            print(f"Tables Found: {len(tables)}")
            print(f"Total Users: {user_count}")
            if "is_active" in user_columns:
                print(f"Active Users: {active_count}")
            print(f"Shopify Stores: {store_count}")

            if missing_columns:
                print(f"\n❌ ISSUES FOUND:")
                print(f"Missing columns: {missing_columns}")
                print("\nTo fix, run: python fix_database_migration.py")
                return False
            else:
                print("\n✅ DATABASE VERIFICATION PASSED")
                print("All required tables and columns are present.")
                return True

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        print(f"\n❌ VERIFICATION ERROR: {e}")

        print("\nCommon causes:")
        print("1. Database connection failed")
        print("2. Environment variables not set")
        print("3. Database not initialized")
        print("4. Missing migration")

        return False


def check_specific_error():
    """Check for the specific is_active column error"""
    try:
        from app import app, db
        from models import User

        with app.app_context():
            # Try to query a user to reproduce the error
            logger.info("🔍 Testing for is_active column error...")

            user = User.query.filter_by(
                email="employee-suite.myshopify.com@shopify.com"
            ).first()

            if user:
                logger.info(f"✅ Found user: {user.email}")
                logger.info(f"User is_active: {user.is_active}")
            else:
                logger.info("No user found with that email")

    except Exception as e:
        if "column users.is_active does not exist" in str(e):
            logger.error("❌ CONFIRMED: is_active column missing!")
            print("\n🚨 PROBLEM CONFIRMED!")
            print("The 'is_active' column is missing from the users table.")
            print(
                "\nFIX: Run 'python fix_database_migration.py' to add the missing column."
            )
        else:
            logger.error(f"❌ Different error: {e}")


if __name__ == "__main__":
    print("🔍 Database Verification Tool")
    print("=" * 30)

    # First check for the specific error
    check_specific_error()

    print("\n" + "-" * 30)

    # Then do full verification
    success = verify_database()

    if not success:
        sys.exit(1)
    else:
        print("\n🎉 Database verification completed successfully!")
