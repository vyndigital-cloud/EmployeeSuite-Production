#!/usr/bin/env python3
"""Quick diagnostic script to find what's broken"""

import sys
import traceback

print("🔍 DIAGNOSING APP ISSUES...\n")

# Test 1: Import check
print("1. Testing imports...")
try:
    from app import app
    print("   ✅ App imports successfully")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 2: App initialization
print("\n2. Testing app initialization...")
try:
    with app.app_context():
        print("   ✅ App context works")
except Exception as e:
    print(f"   ❌ App context failed: {e}")
    traceback.print_exc()

# Test 3: Database connection
print("\n3. Testing database...")
try:
    from models import db
    with app.app_context():
        db.engine.connect()
        print("   ✅ Database connection works")
except Exception as e:
    print(f"   ❌ Database failed: {e}")
    traceback.print_exc()

# Test 4: Routes
print("\n4. Testing routes...")
try:
    routes = list(app.url_map.iter_rules())
    print(f"   ✅ Found {len(routes)} routes")
    critical = ['/', '/dashboard', '/health']
    for route in critical:
        found = any(str(r.rule) == route for r in routes)
        status = "✅" if found else "❌"
        print(f"   {status} {route}")
except Exception as e:
    print(f"   ❌ Routes check failed: {e}")
    traceback.print_exc()

# Test 5: Blueprints
print("\n5. Testing blueprints...")
try:
    blueprint_names = [bp.name for bp in app.blueprints.values()]
    print(f"   ✅ Found {len(blueprint_names)} blueprints: {', '.join(blueprint_names)}")
except Exception as e:
    print(f"   ❌ Blueprints check failed: {e}")
    traceback.print_exc()

# Test 6: Try to start server (just check, don't actually start)
print("\n6. Testing server configuration...")
try:
    port = int(app.config.get('PORT', 5000))
    print(f"   ✅ Port configured: {port}")
    print(f"   ✅ Secret key: {'Set' if app.config.get('SECRET_KEY') else 'Missing'}")
except Exception as e:
    print(f"   ❌ Server config failed: {e}")
    traceback.print_exc()

print("\n" + "="*50)
print("✅ DIAGNOSIS COMPLETE")
print("="*50)
print("\nIf you see errors above, those are the issues to fix.")
print("If everything shows ✅, the app should work. What error are you seeing?")

