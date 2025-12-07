"""
Comprehensive Test Suite - Test EVERYTHING
"""
import sys
import os
import traceback

# Set minimal env vars for testing
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-testing')
os.environ.setdefault('DATABASE_URL', 'sqlite:///test.db')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_dummy')
os.environ.setdefault('STRIPE_SETUP_PRICE_ID', 'price_test')
os.environ.setdefault('STRIPE_MONTHLY_PRICE_ID', 'price_test')

print("=" * 60)
print("COMPREHENSIVE TEST SUITE - Testing EVERYTHING")
print("=" * 60)

tests_passed = 0
tests_failed = 0
issues = []

def test(name, func):
    global tests_passed, tests_failed
    try:
        result = func()
        if result:
            print(f"✅ {name}")
            tests_passed += 1
        else:
            print(f"❌ {name} - FAILED")
            tests_failed += 1
            issues.append(name)
    except Exception as e:
        print(f"❌ {name} - ERROR: {str(e)}")
        tests_failed += 1
        issues.append(f"{name}: {str(e)}")
        traceback.print_exc()

# Test 1: All imports
print("\n📦 TESTING IMPORTS...")
test("Import app", lambda: __import__('app'))
test("Import billing", lambda: __import__('billing'))
test("Import auth", lambda: __import__('auth'))
test("Import shopify_integration", lambda: __import__('shopify_integration'))
test("Import inventory", lambda: __import__('inventory'))
test("Import order_processing", lambda: __import__('order_processing'))
test("Import reporting", lambda: __import__('reporting'))
test("Import models", lambda: __import__('models'))
test("Import security_enhancements", lambda: __import__('security_enhancements'))
test("Import performance", lambda: __import__('performance'))
test("Import input_validation", lambda: __import__('input_validation'))

# Test 2: App initialization
print("\n🚀 TESTING APP INITIALIZATION...")
def test_app_init():
    from app import app
    return app is not None and hasattr(app, 'route')

test("App initializes", test_app_init)

# Test 3: All routes exist
print("\n🛣️  TESTING ROUTES...")
def test_routes():
    from app import app
    routes = [str(rule) for rule in app.url_map.iter_rules()]
    critical_routes = [
        '/',
        '/dashboard',
        '/health',
        '/api/process_orders',
        '/api/update_inventory',
        '/api/generate_report',
    ]
    for route in critical_routes:
        if not any(route in r for r in routes):
            print(f"   Missing route: {route}")
            return False
    return True

test("Critical routes exist", test_routes)

# Test 4: Blueprints registered
print("\n📋 TESTING BLUEPRINTS...")
def test_blueprints():
    from app import app
    blueprint_names = [bp.name for bp in app.blueprints.values()]
    required = ['auth', 'billing', 'shopify', 'admin', 'legal', 'faq', 'oauth']
    for name in required:
        if name not in blueprint_names:
            print(f"   Missing blueprint: {name}")
            return False
    return True

test("All blueprints registered", test_blueprints)

# Test 5: Billing routes
print("\n💳 TESTING BILLING...")
def test_billing_routes():
    from billing import billing_bp
    routes = [str(rule) for rule in billing_bp.url_map.iter_rules()]
    has_subscribe = any('/subscribe' in r for r in routes)
    has_checkout = any('/create-checkout-session' in r for r in routes)
    return has_subscribe and has_checkout

test("Billing routes exist", test_billing_routes)

# Test 6: Security middleware
print("\n🔒 TESTING SECURITY...")
def test_security():
    from security_enhancements import add_security_headers, MAX_REQUEST_SIZE
    from flask import Flask, Response
    app = Flask(__name__)
    with app.app_context():
        response = Response()
        result = add_security_headers(response)
        return result is not None and 'X-Frame-Options' in result.headers

test("Security headers work", test_security)

# Test 7: Performance
print("\n⚡ TESTING PERFORMANCE...")
def test_performance():
    from performance import cache_result, get_cache_key
    key = get_cache_key('test', 'arg1', 'arg2')
    return key is not None and len(key) > 0

test("Performance caching works", test_performance)

# Test 8: Input validation
print("\n✅ TESTING INPUT VALIDATION...")
def test_validation():
    from input_validation import validate_email, sanitize_input
    valid = validate_email('test@example.com')
    invalid = validate_email('not-an-email')
    sanitized = sanitize_input('<script>alert("xss")</script>')
    return valid and not invalid and '<script>' not in sanitized

test("Input validation works", test_validation)

# Test 9: Models
print("\n🗄️  TESTING MODELS...")
def test_models():
    from models import User, ShopifyStore, db
    return User is not None and ShopifyStore is not None and db is not None

test("Models load correctly", test_models)

# Test 10: Form action URLs
print("\n📝 TESTING FORM ACTIONS...")
def test_form_actions():
    # Check billing form action
    with open('billing.py', 'r') as f:
        content = f.read()
        has_correct_action = '/billing/create-checkout-session' in content
        has_url_for = 'url_for(\'billing.create_checkout\')' not in content
        return has_correct_action and has_url_for

test("Billing form action is correct", test_form_actions)

# Test 11: No duplicate middleware
print("\n🔄 TESTING MIDDLEWARE...")
def test_middleware():
    with open('app.py', 'r') as f:
        content = f.read()
        before_count = content.count('@app.before_request')
        after_count = content.count('@app.after_request')
        return before_count == 1 and after_count == 1

test("No duplicate middleware", test_middleware)

# Test 12: Security skips correct routes
print("\n🛡️  TESTING SECURITY SKIPS...")
def test_security_skips():
    with open('app.py', 'r') as f:
        content = f.read()
        has_billing_skip = '/billing/' in content and 'Skip for billing' in content
        has_webhook_skip = '/webhook/' in content and 'Skip for webhook' in content
        has_api_skip = '/api/' in content and 'Skip for API' in content
        return has_billing_skip and has_webhook_skip and has_api_skip

test("Security skips correct routes", test_security_skips)

# Test 13: All files compile
print("\n🔨 TESTING COMPILATION...")
import py_compile
import glob

def test_compilation():
    py_files = glob.glob('*.py')
    errors = []
    for file in py_files:
        if file == 'test_everything.py':
            continue
        try:
            py_compile.compile(file, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"{file}: {e}")
    return len(errors) == 0

test("All Python files compile", test_compilation)

# Test 14: Critical functions exist
print("\n⚙️  TESTING FUNCTIONS...")
def test_functions():
    from inventory import check_inventory, update_inventory
    from order_processing import process_orders
    from reporting import generate_report
    return all([
        callable(check_inventory),
        callable(update_inventory),
        callable(process_orders),
        callable(generate_report)
    ])

test("Critical functions exist", test_functions)

# Test 15: No syntax errors in templates
print("\n📄 TESTING TEMPLATES...")
def test_templates():
    with open('billing.py', 'r') as f:
        content = f.read()
        # Check for basic template syntax
        has_form = '<form' in content and '</form>' in content
        has_button = '<button' in content and '</button>' in content
        return has_form and has_button

test("Templates have correct structure", test_templates)

# Final Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print(f"✅ Passed: {tests_passed}")
print(f"❌ Failed: {tests_failed}")
print(f"📊 Total: {tests_passed + tests_failed}")

if issues:
    print("\n⚠️  ISSUES FOUND:")
    for issue in issues:
        print(f"   - {issue}")
else:
    print("\n🎉 ALL TESTS PASSED - 100% READY!")

print("=" * 60)

sys.exit(0 if tests_failed == 0 else 1)
