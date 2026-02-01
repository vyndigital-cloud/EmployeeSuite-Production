#!/usr/bin/env python3
"""
EMERGENCY PRODUCTION FIX - RUN NOW
==================================

This script immediately fixes the production database issue:
"column users.is_active does not exist"

Run this command to fix the production error right now:
python fix_production_now.py

Safe to run multiple times. Will only add missing columns.
"""

import os
import sys


def fix_now():
    """Fix the production database immediately"""
    try:
        # Quick fix - just add the missing column
        from sqlalchemy import text

        from app import app, db

        with app.app_context():
            print("🚀 FIXING PRODUCTION DATABASE...")

            # Add is_active column if missing
            try:
                db.session.execute(
                    text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
                )
                db.session.commit()
                print("✅ Added is_active column")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print("✅ is_active column already exists")
                else:
                    raise

            # Add email_verified column if missing
            try:
                db.session.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE"
                    )
                )
                db.session.commit()
                print("✅ Added email_verified column")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print("✅ email_verified column already exists")
                else:
                    raise

            # Test the fix
            result = db.session.execute(
                text("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
            )
            count = result.fetchone()[0]

            print(f"🎉 PRODUCTION FIXED! Found {count} active users")
            print("The OAuth error should be resolved now.")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    fix_now()
