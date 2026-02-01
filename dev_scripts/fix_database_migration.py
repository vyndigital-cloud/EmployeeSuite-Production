#!/usr/bin/env python3
"""
EMERGENCY DATABASE MIGRATION FIX
================================

This script fixes the immediate issue where the production database
is missing the 'is_active' column that the application code expects.

This script:
1. Checks if the is_active column exists
2. Adds it if missing
3. Sets default value for existing users
4. Handles both PostgreSQL and SQLite

Run this script to fix the production database immediately:
python fix_database_migration.py
"""

import logging
import os
import sys

from sqlalchemy import inspect, text

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def fix_database():
    """Fix the database by adding missing columns"""
    try:
        # Import the app and database
        from app import app, db

        with app.app_context():
            logger.info("🔧 Starting database migration fix...")

            # Get database inspector
            inspector = inspect(db.engine)

            # Check current columns in users table
            user_columns = [col["name"] for col in inspector.get_columns("users")]
            logger.info(f"Current user columns: {user_columns}")

            # Check if is_active column exists
            if "is_active" not in user_columns:
                logger.info("❌ is_active column missing - adding it now...")

                # Add the column
                db.session.execute(
                    text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
                )

                # Update existing users to have is_active = true
                result = db.session.execute(
                    text("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")
                )

                # Commit the changes
                db.session.commit()

                logger.info(
                    f"✅ Successfully added is_active column and updated {result.rowcount} existing users"
                )
            else:
                logger.info("✅ is_active column already exists")

            # Also check email_verified column while we're at it
            if "email_verified" not in user_columns:
                logger.info("❌ email_verified column missing - adding it now...")

                db.session.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE"
                    )
                )
                db.session.commit()

                logger.info("✅ Successfully added email_verified column")
            else:
                logger.info("✅ email_verified column already exists")

            # Verify the fix by checking columns again
            user_columns_after = [col["name"] for col in inspector.get_columns("users")]
            logger.info(f"Columns after migration: {user_columns_after}")

            # Test a simple query to ensure everything works
            result = db.session.execute(
                text("SELECT COUNT(*) as count FROM users WHERE is_active = TRUE")
            )
            active_users = result.fetchone()[0]
            logger.info(f"✅ Migration successful! Found {active_users} active users")

            print("\n" + "=" * 60)
            print("🎉 DATABASE MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print(
                f"✅ is_active column: {'EXISTS' if 'is_active' in user_columns_after else 'MISSING'}"
            )
            print(
                f"✅ email_verified column: {'EXISTS' if 'email_verified' in user_columns_after else 'MISSING'}"
            )
            print(f"✅ Active users count: {active_users}")
            print("\nYour application should now work without the column error!")
            print("=" * 60)

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.session.rollback()
        print(f"\n❌ ERROR: {e}")
        print("\nThis might happen if:")
        print("1. Database connection failed")
        print("2. Permissions insufficient")
        print("3. Column already exists (check logs above)")
        sys.exit(1)


if __name__ == "__main__":
    print("🚀 Starting Emergency Database Migration Fix...")
    print("This will add the missing 'is_active' column to fix the production error.")
    print("-" * 60)

    fix_database()
