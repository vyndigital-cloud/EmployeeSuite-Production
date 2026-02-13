import os
import unittest
from app_factory import create_app
from models import db, User, ShopifyStore

# Set env vars
os.environ['ADMIN_PASSWORD'] = 'admin_test_123'
os.environ['SHOPIFY_API_KEY'] = 'test_key'
os.environ['SHOPIFY_API_SECRET'] = 'test_secret'

class AdminDeleteTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        # Create a test user to delete
        self.user = User(email='delete_me@example.com')
        self.user.set_password('password123')
        db.session.add(self.user)
        db.session.commit()
        self.user_id = self.user.id
        print(f"Created user {self.user_id} to delete")

    def tearDown(self):
        # Cleanup if delete failed
        if User.query.get(self.user_id):
            db.session.delete(User.query.get(self.user_id))
            db.session.commit()
        self.ctx.pop()

    def test_admin_delete_user(self):
        # 1. Login as Admin
        with self.client.session_transaction() as sess:
            sess['admin_logged_in'] = True
        
        # 2. Delete User
        # The route is POST /system-admin/delete-user/<user_id>
        print(f"Attempting to delete user {self.user_id}...")
        resp = self.client.post(f'/system-admin/delete-user/{self.user_id}', follow_redirects=True)
        
        print(f"Delete response status: {resp.status_code}")
        
        # 3. Verify User is Gone
        deleted_user = User.query.get(self.user_id)
        if deleted_user:
            print("❌ User still exists in DB!")
        else:
            print("✅ User successfully deleted from DB")
            
        self.assertIsNone(deleted_user)

if __name__ == '__main__':
    unittest.main()
