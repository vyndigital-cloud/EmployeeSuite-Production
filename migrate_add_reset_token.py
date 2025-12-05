"""
Database migration script to add reset_token columns to users table.
Safe to run multiple times - checks if columns exist first.
"""
import os
import sys
from app import app, db

def migrate():
    """Add reset_token and reset_token_expires columns to users table"""
    with app.app_context():
        try:
            # Check if columns already exist
            result = db.session.execute(db.text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='reset_token'
            """))
            
            if result.fetchone():
                print("✅ reset_token column already exists - skipping migration")
                return
            
            # Add columns
            print("Adding reset_token columns to users table...")
            db.session.execute(db.text("""
                ALTER TABLE users 
                ADD COLUMN reset_token VARCHAR(100),
                ADD COLUMN reset_token_expires TIMESTAMP
            """))
            db.session.commit()
            print("✅ Migration successful! reset_token columns added.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration error: {e}")
            # Check if it's because columns already exist (different error format)
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("✅ Columns already exist - migration not needed")
            else:
                raise

if __name__ == '__main__':
    migrate()

