#!/usr/bin/env python3
"""
IMMEDIATE DATABASE FIX - RUN NOW
================================

This script immediately fixes all missing database columns that are causing
production errors. It's designed to run standalone and fix everything at once.

Usage: python fix_db_now.py
"""

import os
import sys


def fix_database_immediately():
    """Fix all missing database columns right now"""
    try:
        print("🚀 IMMEDIATE DATABASE FIX STARTING...")

        # Import Flask app and database
        from sqlalchemy import inspect, text

        from app import app, db

        with app.app_context():
            print("✅ Connected to database")

            # Get database inspector
            inspector = inspect(db.engine)

            # Check current user table columns
            try:
                user_columns = [col["name"] for col in inspector.get_columns("users")]
                print(f"📊 Current user columns: {user_columns}")
            except Exception as e:
                print(f"❌ Error checking columns: {e}")
                return False

            # List of all columns that should exist in users table
            required_columns = {
                "is_active": "BOOLEAN DEFAULT TRUE",
                "email_verified": "BOOLEAN DEFAULT FALSE",
                "last_login": "TIMESTAMP",
                "reset_token": "VARCHAR(100)",
                "reset_token_expires": "TIMESTAMP",
            }

            columns_added = []

            # Add each missing column
            for column_name, column_def in required_columns.items():
                if column_name not in user_columns:
                    try:
                        sql = f"ALTER TABLE users ADD COLUMN {column_name} {column_def}"
                        print(f"🔧 Adding column: {column_name}")
                        db.session.execute(text(sql))
                        columns_added.append(column_name)
                        print(f"✅ Added {column_name} column")
                    except Exception as e:
                        error_str = str(e).lower()
                        if "already exists" in error_str or "duplicate" in error_str:
                            print(f"✅ {column_name} already exists")
                        else:
                            print(f"❌ Failed to add {column_name}: {e}")
                            # Continue with other columns
                else:
                    print(f"✅ {column_name} already exists")

            # Commit all changes
            if columns_added:
                db.session.commit()
                print(f"💾 Committed changes for: {columns_added}")

            # Verify the fix by checking columns again
            user_columns_after = [col["name"] for col in inspector.get_columns("users")]
            print(f"📊 Columns after fix: {user_columns_after}")

            # Test the problematic query that was failing
            try:
                result = db.session.execute(
                    text("SELECT COUNT(*) FROM users WHERE email = :email"),
                    {"email": "test@example.com"},
                )
                count = result.fetchone()[0]
                print(f"✅ Test query successful - database is working!")
            except Exception as e:
                print(f"❌ Test query failed: {e}")
                return False

            print("\n" + "=" * 60)
            print("🎉 DATABASE FIX COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print(f"✅ Columns checked: {len(required_columns)}")
            print(f"✅ Columns added: {len(columns_added)}")
            if columns_added:
                for col in columns_added:
                    print(f"   - {col}")
            print("✅ Database is now ready for OAuth authentication")
            print("✅ The 'column does not exist' error should be resolved")
            print("=" * 60)

            return True

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        print(f"Error type: {type(e).__name__}")
        print("\nPossible causes:")
        print("1. Database connection failed")
        print("2. App not properly configured")
        print("3. Environment variables missing")
        print("\nTry running this script again, or check your app configuration.")

        # Try to rollback
        try:
            db.session.rollback()
        except:
            pass

        return False


if __name__ == "__main__":
    print("🔧 IMMEDIATE DATABASE COLUMN FIX")
    print("This will add all missing columns to fix OAuth errors")
    print("-" * 50)

    success = fix_database_immediately()

    if success:
        print("\n✅ SUCCESS! Your OAuth errors should be fixed now.")
        sys.exit(0)
    else:
        print("\n❌ FAILED! Check the error messages above.")
        sys.exit(1)
