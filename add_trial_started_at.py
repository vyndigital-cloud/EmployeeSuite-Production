"""
Migration script to add trial_started_at column to users table
Run this once to fix the database schema
"""
from app_factory import create_app
from models import db
from sqlalchemy import text, inspect

def add_trial_started_at_column():
    """Add trial_started_at column if it doesn't exist"""
    app = create_app()
    
    with app.app_context():
        try:
            # Use SQLAlchemy inspector to check if column exists (works with all databases)
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            if 'trial_started_at' not in columns:
                print("Adding trial_started_at column...")
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN trial_started_at TIMESTAMP WITH TIME ZONE
                """))
                db.session.commit()
                print("✅ Successfully added trial_started_at column")
            else:
                print("✅ trial_started_at column already exists")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    add_trial_started_at_column()

