#!/usr/bin/env python3
"""
Comprehensive App Functionality Verification
Tests critical app functionality before deployment
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🧪 APP FUNCTIONALITY VERIFICATION")
print("=" * 50)
print("")

PASSED = 0
FAILED = 0

def test(name, func):
    """Run a test and track results"""
    global PASSED, FAILED
    try:
        print(f"Testing: {name}... ", end="", flush=True)
        result = func()
        if result:
            print("✅ PASS")
            PASSED += 1
            return True
        else:
            print("❌ FAIL")
            FAILED += 1
            return False
    except Exception as e:
        print(f"❌ FAIL ({str(e)})")
        FAILED += 1
        return False

# Test 1: App imports
def test_app_imports():
    try:
        from app import app
        return app is not None
    except Exception:
        return False

# Test 2: Database models
def test_models():
    try:
        from models import db, User, ShopifyStore
        return db is not None and User is not None and ShopifyStore is not None
    except Exception:
        return False

# Test 3: Blueprints
def test_blueprints():
    try:
        from app import app
        required = ['auth', 'billing', 'shopify', 'oauth', 'gdpr_compliance', 'webhook_shopify']
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        return all(name in blueprint_names for name in required)
    except Exception:
        return False

# Test 4: Routes exist
def test_routes():
    try:
        from app import app
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        required = ['/', '/dashboard', '/health', '/login', '/billing/subscribe']
        return all(any(route.startswith(req) for route in routes) for req in required)
    except Exception:
        return False

# Test 5: OAuth routes
def test_oauth_routes():
    try:
        from shopify_oauth import oauth_bp
        routes = [str(rule) for rule in oauth_bp.url_map.iter_rules()]
        return any('/install' in route for route in routes) and any('/callback' in route or '/auth/callback' in route for route in routes)
    except Exception:
        return False

# Test 6: Webhook routes
def test_webhook_routes():
    try:
        from webhook_shopify import webhook_shopify_bp
        routes = [str(rule) for rule in webhook_shopify_bp.url_map.iter_rules()]
        return any('uninstall' in route for route in routes) and any('subscription' in route for route in routes)
    except Exception:
        return False

# Test 7: GDPR routes
def test_gdpr_routes():
    try:
        from gdpr_compliance import gdpr_bp
        routes = [str(rule) for rule in gdpr_bp.url_map.iter_rules()]
        required_terms = ['data_request', 'redact']
        return all(any(term in route for route in routes) for term in required_terms)
    except Exception:
        return False

# Test 8: Session token verification
def test_session_tokens():
    try:
        from session_token_verification import verify_session_token
        return verify_session_token is not None
    except Exception:
        return False

# Test 9: HMAC verification
def test_hmac_verification():
    try:
        from gdpr_compliance import verify_shopify_webhook
        from webhook_shopify import verify_shopify_webhook as verify_webhook
        return verify_shopify_webhook is not None and verify_webhook is not None
    except Exception:
        return False

# Test 10: App context works
def test_app_context():
    try:
        from app import app
        with app.app_context():
            from models import db
            # Just test that we can create a connection
            db.engine.connect()
            return True
    except Exception:
        return False

# Run all tests
print("📋 Running functionality tests...")
print("")

test("App imports", test_app_imports)
test("Database models", test_models)
test("Blueprints registered", test_blueprints)
test("Critical routes exist", test_routes)
test("OAuth routes", test_oauth_routes)
test("Webhook routes", test_webhook_routes)
test("GDPR routes", test_gdpr_routes)
test("Session token verification", test_session_tokens)
test("HMAC verification", test_hmac_verification)
test("App context", test_app_context)

print("")
print("=" * 50)
print("📊 TEST SUMMARY")
print("=" * 50)
print(f"✅ Passed: {PASSED}")
print(f"❌ Failed: {FAILED}")
print("")

if FAILED > 0:
    print("❌ FUNCTIONALITY VERIFICATION FAILED")
    print("Please fix the failing tests before deployment.")
    sys.exit(1)
else:
    print("✅ ALL FUNCTIONALITY TESTS PASSED")
    sys.exit(0)

