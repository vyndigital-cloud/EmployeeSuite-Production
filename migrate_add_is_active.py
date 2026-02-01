"""
Database migration script to add is_active column to users table.
Safe to run multiple times - checks if column exists first.
"""

import os
import sys

from app import app, db


def migrate():
    """Add is_active column to users table"""
    with app.app_context():
        try:
            # Get database dialect to determine which method to use
            dialect = db.engine.dialect.name

            if dialect == "sqlite":
                # For SQLite, just try to add column and catch "already exists" errors
                try:
                    print("Adding is_active column to users table...")
                    db.session.execute(
                        db.text("""
                        ALTER TABLE users
                        ADD COLUMN is_active BOOLEAN DEFAULT TRUE
                    """)
                    )
                    db.session.commit()
                    print("✅ is_active column added successfully")
                except Exception as e:
                    error_str = str(e).lower()
                    if "duplicate column" in error_str or "already exists" in error_str:
                        print("✅ is_active column already exists")
                    else:
                        raise
            else:
                # For PostgreSQL, check information_schema first
                result = db.session.execute(
                    db.text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name='users' AND column_name='is_active'
                """)
                )

                if result.fetchone():
                    print("✅ is_active column already exists - skipping migration")
                    return

                # Add column
                print("Adding is_active column to users table...")
                db.session.execute(
                    db.text("""
                    ALTER TABLE users
                    ADD COLUMN is_active BOOLEAN DEFAULT TRUE
                """)
                )
                db.session.commit()
                print("✅ Migration successful! is_active column added.")

                # Update existing users to have is_active = true if null
                print("Updating existing users to set is_active = true...")
                db.session.execute(
                    db.text("""
                    UPDATE users
                    SET is_active = TRUE
                    WHERE is_active IS NULL
                """)
                )
                db.session.commit()
                print("✅ Updated existing users with is_active = true")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration error: {e}")
            # Check if it's because column already exists (different error format)
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("✅ Column already exists - migration not needed")
            else:
                raise


if __name__ == "__main__":
    migrate()
