import os
import sys
from sqlalchemy import create_engine, text

# 1. Grab your URI (Make sure this matches your .env or Render var)
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("❌ CRITICAL: DATABASE_URL environment variable is missing.")
    sys.exit(1)

# Enforce SSL if using postgresql (Render/Neon requirement)
if "postgresql://" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    print("⚠️  Warning: SSL mode missing in DATABASE_URL. Attempting to add it...")
    if "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"
    else:
        DATABASE_URL += "?sslmode=require"

print(f"ℹ️  Targeting DB: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'LOCAL/UNKNOWN'}")

# 2. The "Hardened" Engine
# This is what moves your probability. It pings the DB before it speaks.
try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # This is the "Magic" line
        pool_recycle=280     # Kills the connection before Neon's 300s reaper
    )
except Exception as e:
    print(f"❌ Engine Creation Failed: {e}")
    sys.exit(1)

def run_diagnostic():
    print("🚀 Starting Deep Scan v2 (Hardened)...")
    try:
        with engine.connect() as conn:
            # Test 1: Connectivity
            print("✅ Step 1: Physical connection established.")
            
            # Test 2: Handshake (The Wake-up)
            result = conn.execute(text("SELECT 1")).fetchone()
            print(f"✅ Step 2: Database is AWAKE (Result: {result[0]})")
            
            # Test 3: Schema Check (The "Fucked Code" Finder)
            # We check 'users' table specifically as it's critical for the landing page
            try:
                table_check = conn.execute(text("SELECT count(*) FROM users")).fetchone()
                print(f"✅ Step 3: Schema is ALIVE (Found {table_check[0]} records)")
            except Exception as schema_error:
                print(f"❌ Step 3 FAILED: Schema missing or corrupt. Error: {schema_error}")
                print("👉 Fix: Tables are missing. You need to run: flask db upgrade")
                return

            print("\n🎉 DIAGNOSIS: The Database is HEALTHY. If the app is still crashing, check your application logs (app_factory.py).")
            
    except Exception as e:
        error_str = str(e)
        print(f"\n❌ CRITICAL FAILURE: {error_str}")
        
        if "SSL" in error_str or "certificate" in error_str:
            print("\n👉 Fix: Your connection string needs '?sslmode=require'. Update DATABASE_URL in Render.")
        elif "remaining connection slots" in error_str or "too many clients" in error_str:
            print("\n👉 Fix: You hit the Neon 10-connection limit. Restart the service to clear ghosts or kill local tabs!")
        elif "relation" in error_str and "does not exist" in error_str:
             print("\n👉 Fix: The 'users' table is missing. You need to run: flask db upgrade")
        elif "password" in error_str or "authentication" in error_str:
             print("\n👉 Fix: Invalid credentials. Check DATABASE_URL username/password.")

if __name__ == "__main__":
    run_diagnostic()
