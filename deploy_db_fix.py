
import os
import sys
import sqlalchemy
from sqlalchemy import text

def deploy_fix():
    print("🚀 Database Fix Deployer")
    print("========================")
    print("This script will run 'optimize_db.sql' against your database.")
    
    
    # Get DB URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("\n⚠️  DATABASE_URL not set in environment.")
        # Default to local SQLite if not set
        print("👉 Defaulting to local SQLite: sqlite:///app.db")
        db_url = "sqlite:///app.db"

    if not db_url:
        print("❌ No database URL provided. Exiting.")
        sys.exit(1)

    # Allow both Postgres and SQLite
    if not (db_url.startswith("postgres") or db_url.startswith("sqlite")):
        print("❌ URL must be postgres... or sqlite...")
        sys.exit(1)
        
    # Fix postgres:// legacy URLs for SQLAlchemy 1.4+
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    try:
        print(f"\nCONNECTING to database...")
        engine = sqlalchemy.create_engine(db_url)
        connection = engine.connect()
        print("✅ Connected successfully.")
        
        # Read SQL file
        try:
            with open("optimize_db.sql", "r") as f:
                sql_content = f.read()
        except FileNotFoundError:
            print("❌ 'optimize_db.sql' not found in current directory.")
            sys.exit(1)

        print("\nRUNNING migration...")
        # Split by ; for rudimentary statement parsing if needed, but text() often handles blocks.
        # However, for safety and better error reporting, executing the whole block is usually fine with psycopg2.
        # But let's try statement by statement to be safe.
        statements = sql_content.split(';')
        
        trans = connection.begin()
        count = 0
        try:
            for statement in statements:
                if statement.strip():
                    connection.execute(text(statement))
                    count += 1
            trans.commit()
            print(f"✅ Executed {count} SQL statements.")
            print("\n🎉 SUCCESS! Database schema is now optimized.")
            print("You can now restart your Render service.")
            
        except Exception as e:
            trans.rollback()
            print(f"\n❌ SQL Error: {e}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Connection Error: {e}")
        print("Check your password and firewall rules.")
        sys.exit(1)
        
if __name__ == "__main__":
    deploy_fix()
