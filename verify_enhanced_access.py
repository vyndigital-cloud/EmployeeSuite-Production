import os
from app_factory import create_app
from models import db, User, ShopifyStore

# Set env vars to avoid startup errors
os.environ['ADMIN_PASSWORD'] = 'admin_test_123'
os.environ['SHOPIFY_API_KEY'] = 'test_key'
os.environ['SHOPIFY_API_SECRET'] = 'test_secret'

app = create_app()

def verify_access():
    with app.app_context():
        # Setup Test User
        email = 'enhanced_test@example.com'
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            print(f"Created user {user.id}")
        else:
            print(f"Found user {user.id}")

        # Create dummy store if needed for the endpoint to not 404 immediately
        store = ShopifyStore.query.filter_by(user_id=user.id).first()
        if not store:
            store = ShopifyStore(
                user_id=user.id,
                shop_url='test-enhanced.myshopify.com',
                access_token='dummy_token',
                is_active=True
            )
            db.session.add(store)
            db.session.commit()

        # TEST 1: Unsubscribed
        print("\n--- Test 1: Unsubscribed Access ---")
        user.is_subscribed = False
        db.session.commit()

        with app.test_client() as client:
            # Simulate Login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Hit protected endpoint
            resp = client.get('/api/export/orders')
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 403:
                print("✅ Correctly denied access (403)")
            else:
                print(f"❌ Failed: Expected 403, got {resp.status_code}")

        # Clear cache to ensure fresh check
        User._access_cache.clear()

        # TEST 2: Subscribed
        print("\n--- Test 2: Subscribed Access ---")
        user.is_subscribed = True
        db.session.commit()

        with app.test_client() as client:
            # Simulate Login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Hit protected endpoint
            resp = client.get('/api/export/orders')
            print(f"Status Code: {resp.status_code}")
            
            # We expect !403. It might be 500 (API error) or 404, but NOT 403.
            if resp.status_code != 403:
                print(f"✅ Correctly allowed access (Status: {resp.status_code})")
            else:
                print("❌ Failed: Still got 403")

if __name__ == "__main__":
    verify_access()
