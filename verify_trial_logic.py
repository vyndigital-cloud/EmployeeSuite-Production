import os
import unittest
from datetime import datetime, timedelta, timezone
from app_factory import create_app
from models import db, User, ShopifyStore

class TestTrialLogic(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_trial_expiry_gate(self):
        """Test that expired trial users get 403 Forbidden with subscribe action"""
        # Create expired user
        user = User(email="expired@example.com")
        user.set_password("password123")
        # Set trial to have ended yesterday
        user.trial_ends_at = datetime.now(timezone.utc) - timedelta(days=1)
        user.is_subscribed = False
        db.session.add(user)
        db.session.commit()

        # Create dummy store for them (needed for some logic, but mainly user check)
        store = ShopifyStore(user_id=user.id, shop_url="expired-test.myshopify.com", access_token="shpat_test")
        db.session.add(store)
        db.session.commit()

        # Login as this user
        with self.app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True

            # Attempt to access protected resource
            # We need to login first via Flask-Login. 
            # In test_client, setting session _user_id usually works if LoginManager is configured.
            
            # Let's hit the api endpoint
            response = client.post('/api/process_orders')
            
            print(f"Response Status: {response.status_code}")
            print(f"Response JSON: {response.json}")

            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json['action'], 'subscribe')
            print("✅ SUCCESS: Expired user was gated with 'subscribe' action.")

if __name__ == '__main__':
    unittest.main()
