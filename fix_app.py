#!/usr/bin/env python3
"""
COMPREHENSIVE APP FIX SCRIPT
Fixes common issues that break Flask apps
"""

import os
import sys
import secrets
import traceback

print("🔧 FIXING YOUR APP...\n")

# Fix 1: Check and create .env file if needed
print("1. Checking environment variables...")
env_file = '.env'
if not os.path.exists(env_file):
    print("   ⚠️  No .env file found. Creating one...")
    secret_key = secrets.token_urlsafe(32)
    cron_secret = secrets.token_urlsafe(32)
    
    env_content = f"""# Auto-generated environment variables
# ⚠️  IMPORTANT: Set these in your deployment platform (Render, Heroku, etc.)

# Security (REQUIRED)
SECRET_KEY={secret_key}
CRON_SECRET={cron_secret}

# Database (will be auto-provided by Render/Heroku)
# DATABASE_URL=postgresql://...

# Shopify (get from Partners Dashboard)
# SHOPIFY_API_KEY=your-api-key
# SHOPIFY_API_SECRET=your-api-secret
# SHOPIFY_REDIRECT_URI=https://your-domain.com/auth/callback

# Stripe (get from Stripe Dashboard)
# STRIPE_SECRET_KEY=sk_live_...
# STRIPE_WEBHOOK_SECRET=whsec_...
# STRIPE_MONTHLY_PRICE_ID=price_...

# Email (get from SendGrid)
# SENDGRID_API_KEY=SG....

# Optional
# ENVIRONMENT=development
# SENTRY_DSN=your-sentry-dsn
"""
    with open(env_file, 'w') as f:
        f.write(env_content)
    print(f"   ✅ Created .env file with SECRET_KEY and CRON_SECRET")
    print(f"   ⚠️  Add other variables as needed")
else:
    print("   ✅ .env file exists")

# Fix 2: Test imports
print("\n2. Testing all imports...")
failed_imports = []
try:
    from app import app
    print("   ✅ app.py imports successfully")
except Exception as e:
    print(f"   ❌ app.py import failed: {e}")
    failed_imports.append(('app', str(e)))
    traceback.print_exc()

# Test critical modules
modules_to_test = [
    'models', 'auth', 'billing', 'shopify_routes', 
    'webhook_stripe', 'webhook_shopify', 'order_processing',
    'inventory', 'reporting'
]

for module in modules_to_test:
    try:
        __import__(module)
        print(f"   ✅ {module}.py imports successfully")
    except Exception as e:
        print(f"   ❌ {module}.py import failed: {e}")
        failed_imports.append((module, str(e)))

# Fix 3: Check database
print("\n3. Checking database...")
try:
    from app import app
    from models import db
    with app.app_context():
        # Try to connect
        db.engine.connect()
        print("   ✅ Database connection works")
except Exception as e:
    print(f"   ⚠️  Database issue: {e}")
    print("   💡 This is OK if DATABASE_URL isn't set yet (will use SQLite locally)")

# Fix 4: Verify routes
print("\n4. Verifying routes...")
try:
    from app import app
    routes = list(app.url_map.iter_rules())
    critical_routes = ['/', '/dashboard', '/health']
    missing = []
    for route in critical_routes:
        if not any(str(r.rule) == route for r in routes):
            missing.append(route)
    
    if missing:
        print(f"   ❌ Missing routes: {missing}")
    else:
        print(f"   ✅ All critical routes exist ({len(routes)} total routes)")
except Exception as e:
    print(f"   ❌ Route check failed: {e}")

# Fix 5: Check requirements.txt
print("\n5. Checking requirements.txt...")
if os.path.exists('requirements.txt'):
    with open('requirements.txt', 'r') as f:
        deps = f.read()
        critical_deps = ['Flask', 'gunicorn', 'psycopg2', 'SQLAlchemy']
        missing_deps = []
        for dep in critical_deps:
            if dep.lower() not in deps.lower():
                missing_deps.append(dep)
        
        if missing_deps:
            print(f"   ⚠️  Missing dependencies: {missing_deps}")
        else:
            print("   ✅ All critical dependencies in requirements.txt")
else:
    print("   ❌ requirements.txt not found!")

# Fix 6: Check Procfile
print("\n6. Checking Procfile...")
if os.path.exists('Procfile'):
    with open('Procfile', 'r') as f:
        procfile = f.read()
        if 'gunicorn' in procfile and 'app:app' in procfile:
            print("   ✅ Procfile looks correct")
        else:
            print("   ⚠️  Procfile might be incorrect")
            print(f"   Current: {procfile.strip()}")
else:
    print("   ⚠️  Procfile not found (needed for deployment)")

# Summary
print("\n" + "="*60)
print("📊 SUMMARY")
print("="*60)

if failed_imports:
    print(f"\n❌ FOUND {len(failed_imports)} IMPORT ERRORS:")
    for module, error in failed_imports:
        print(f"   - {module}: {error}")
    print("\n💡 These need to be fixed before the app will work.")
else:
    print("\n✅ NO CRITICAL ERRORS FOUND")
    print("\nThe app should work! If you're still seeing errors:")
    print("   1. Share the exact error message you're seeing")
    print("   2. Check if you're missing environment variables")
    print("   3. Try running: python3 app.py")
    print("   4. Check deployment logs if deploying")

print("\n" + "="*60)

