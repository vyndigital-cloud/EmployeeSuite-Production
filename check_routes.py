
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Mock environment before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'testing-secret'
os.environ['SHOPIFY_API_KEY'] = 'test-key'
os.environ['SHOPIFY_API_SECRET'] = 'test-secret'

# Mock Shopify verification
sys.modules['session_token_verification'] = MagicMock()
sys.modules['session_token_verification'].verify_session_token = lambda x: x

try:
    from main import app
    from models import db, User
except ImportError as e:
    print(f"FAILED to import app: {e}")
    sys.exit(1)

class TestRoutes(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()
            # Create test user
            user = User(shopify_id=12345, email="test@example.com")
            db.session.add(user)
            db.session.commit()

    def test_health_check(self):
        print("\nTesting /health...")
        response = self.client.get('/health')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
             print("✅ Health Check Passed")
        else:
             print(f"❌ Health Check Failed: {response.json}")

    def test_dashboard_access_no_auth(self):
        print("\nTesting /dashboard (No Auth)...")
        # Should redirect or error depending on implementation
        try:
            response = self.client.get('/dashboard')
            print(f"Status: {response.status_code}")
            # Likely 401, 302, or 500 if auth is strict
        except Exception as e:
            print(f"❌ Dashboard Error: {e}")

    def test_api_process_orders(self):
        print("\nTesting /api/process_orders...")
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['shop_id'] = 12345
        
        try:
            response = self.client.get('/api/process_orders')
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ API Process Orders Passed")
            else:
                print(f"❌ API Process Orders Failed: {response.get_json() if response.is_json else response.data}")
        except Exception as e:
             print(f"❌ API Error: {e}")

if __name__ == '__main__':
    unittest.main(failfast=False)
