#!/usr/bin/env python3
"""
PRODUCTION DATABASE DEPLOYMENT FIX
==================================

This script fixes the immediate production issue where the database
is missing required columns that the application code expects.

PROBLEM:
- Production app is failing with: "column users.is_active does not exist"
- The User model in code has is_active column but database doesn't
- This causes 500 errors during OAuth authentication

SOLUTION:
- Add missing columns to production database
- Update existing records with proper defaults
- Verify the fix works
- Safe to run multiple times

USAGE:
python deploy_fix_database.py

This script is designed for immediate production deployment to fix the issue.
"""

import logging
import os
import sys
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def deploy_database_fix():
    """Deploy the database fix to production"""

    print("🚀 PRODUCTION DATABASE FIX DEPLOYMENT")
    print("=" * 50)
    print("This will fix the 'column users.is_active does not exist' error")
    print("by adding missing columns to your production database.")
    print()

    try:
        # Import app components
        logger.info("Importing application components...")
        from sqlalchemy import inspect, text

        from app import app, db

        with app.app_context():
            logger.info("Connected to database successfully")

            # Get database info
            dialect = db.engine.dialect.name
            logger.info(f"Database type: {dialect}")

            # Get inspector to check current schema
            inspector = inspect(db.engine)

            # Check users table columns
            user_columns = [col["name"] for col in inspector.get_columns("users")]
            logger.info(f"Current users table columns: {user_columns}")

            # List of columns that should exist based on current User model
            required_columns = {
                "is_active": "BOOLEAN DEFAULT TRUE",
                "email_verified": "BOOLEAN DEFAULT FALSE",
                "last_login": "TIMESTAMP",
                "reset_token": "VARCHAR(100)",
                "reset_token_expires": "TIMESTAMP",
            }

            added_columns = []

            # Add missing columns
            for column_name, column_def in required_columns.items():
                if column_name not in user_columns:
                    logger.info(f"Adding missing column: {column_name}")

                    try:
                        # Add the column
                        sql = f"ALTER TABLE users ADD COLUMN {column_name} {column_def}"
                        db.session.execute(text(sql))
                        added_columns.append(column_name)
                        logger.info(f"✅ Added column: {column_name}")

                    except Exception as col_error:
                        if "already exists" in str(col_error).lower():
                            logger.info(f"✅ Column {column_name} already exists")
                        else:
                            logger.error(f"❌ Failed to add {column_name}: {col_error}")
                            raise
                else:
                    logger.info(f"✅ Column {column_name} already exists")

            # Commit the schema changes
            if added_columns:
                db.session.commit()
                logger.info(f"Schema changes committed for columns: {added_columns}")

            # Update existing users with proper defaults for new columns
            if "is_active" in added_columns:
                logger.info("Setting is_active=TRUE for existing users...")
                result = db.session.execute(
                    text("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")
                )
                db.session.commit()
                logger.info(f"Updated {result.rowcount} users with is_active=TRUE")

            if "email_verified" in added_columns:
                logger.info("Setting email_verified=FALSE for existing users...")
                result = db.session.execute(
                    text(
                        "UPDATE users SET email_verified = FALSE WHERE email_verified IS NULL"
                    )
                )
                db.session.commit()
                logger.info(
                    f"Updated {result.rowcount} users with email_verified=FALSE"
                )

            # Verify the fix by testing the problematic query
            logger.info("Testing the fix...")

            # Test query that was failing in production
            test_result = db.session.execute(
                text("SELECT id, email, is_active, email_verified FROM users LIMIT 5")
            )

            users = test_result.fetchall()
            logger.info(f"✅ Test query successful - found {len(users)} users")

            # Test the specific OAuth query that was failing
            oauth_test = db.session.execute(
                text("""
                SELECT users.id, users.email, users.is_active, users.email_verified
                FROM users
                WHERE users.email = :email
                LIMIT 1
                """),
                {"email": "test@example.com"},
            )

            logger.info("✅ OAuth-style query test passed")

            # Get final column list to verify
            user_columns_final = [col["name"] for col in inspector.get_columns("users")]

            print()
            print("🎉 DEPLOYMENT FIX COMPLETED SUCCESSFULLY!")
            print("=" * 50)
            print(f"✅ Database Type: {dialect}")
            print(f"✅ Columns Added: {len(added_columns)}")
            if added_columns:
                for col in added_columns:
                    print(f"   - {col}")
            print(f"✅ Total Users Columns: {len(user_columns_final)}")
            print()
            print("VERIFICATION:")
            required_cols = ["is_active", "email_verified"]
            for col in required_cols:
                status = "✅ EXISTS" if col in user_columns_final else "❌ MISSING"
                print(f"   {col}: {status}")

            print()
            print("🚀 PRODUCTION DEPLOYMENT STATUS: READY")
            print("The 'column users.is_active does not exist' error is now fixed!")
            print()
            print("Next steps:")
            print("1. The app should now work without database errors")
            print("2. OAuth authentication should complete successfully")
            print("3. Monitor logs for any remaining issues")
            print()

            return True

    except Exception as e:
        logger.error(f"❌ Deployment fix failed: {e}")

        print()
        print("❌ DEPLOYMENT FIX FAILED!")
        print("=" * 30)
        print(f"Error: {e}")
        print()
        print("Possible causes:")
        print("1. Database connection issue")
        print("2. Insufficient permissions")
        print("3. Database locked")
        print("4. Environment variables not set")
        print()
        print("Check your environment variables:")
        print("- DATABASE_URL")
        print("- FLASK_ENV")
        print("- Other required config")

        # Try to rollback if there's an active transaction
        try:
            db.session.rollback()
        except:
            pass

        return False


def verify_environment():
    """Verify environment is ready for deployment"""
    logger.info("Verifying deployment environment...")

    required_vars = ["DATABASE_URL"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False

    logger.info("✅ Environment verification passed")
    return True


def main():
    """Main deployment function"""
    print("🔧 PRODUCTION DATABASE DEPLOYMENT FIX")
    print("Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))
    print()

    # Verify environment first
    if not verify_environment():
        print("❌ Environment verification failed")
        sys.exit(1)

    # Run the database fix
    success = deploy_database_fix()

    if success:
        print("✅ Deployment fix completed successfully!")
        sys.exit(0)
    else:
        print("❌ Deployment fix failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
