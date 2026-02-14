
import os
import sys
import time

def check_environment():
    print("🚀 STARTING PRE-FLIGHT CHECK...")
    
    # 1. Environment Variables
    print("\n[1/3] Checking Environment Variables...")
    required = ["DATABASE_URL", "SHOPIFY_API_KEY", "SHOPIFY_API_SECRET", "SECRET_KEY"]
    missing = []
    for var in required:
        val = os.getenv(var)
        if not val:
            missing.append(var)
            print(f"❌ {var}: MISSING")
        else:
            masked = val[:8] + "..." if len(val) > 8 else "***"
            print(f"✅ {var}: SET ({masked})")
    
    if missing:
        print(f"🚨 CRITICAL: Missing environment variables: {', '.join(missing)}")
        return False

    # 2. Database Connection
    print("\n[2/3] Checking Database Connection...")
    db_url = os.getenv("DATABASE_URL")
    if db_url.startswith("postgres://"):
        print("⚠️  DETECTED LEGACY PROTOCOL: 'postgres://'. Auto-correcting to 'postgresql://'...")
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database Connection: SUCCESS")
            
            # Check for usage_events table
            formatted_check = text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'usage_events')")
            table_exists = conn.execute(formatted_check).scalar()
            if table_exists:
                print("✅ Table 'usage_events': FOUND")
            else:
                print("⚠️  Table 'usage_events': MISSING (Run migrations!)")

    except Exception as e:
        print(f"❌ Database Connection FAILED: {str(e)}")
        return False

    # 3. Redis Connection
    print("\n[3/3] Checking Redis Connection...")
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("⚠️  REDIS_URL not set. Skipping Redis check.")
    else:
        try:
            import redis
            r = redis.from_url(redis_url)
            r.ping()
            print("✅ Redis Connection: SUCCESS")
        except Exception as e:
            print(f"❌ Redis Connection FAILED: {str(e)}")
            # Don't fail the whole check if Redis is optional for boot, but user said it's required now.
            # Assuming required for "Exit-Grade"
            return False

    print("\n✨ PRE-FLIGHT CHECK COMPLETE: ALL SYSTEMS GO ✨")
    return True

if __name__ == "__main__":
    success = check_environment()
    sys.exit(0 if success else 1)
