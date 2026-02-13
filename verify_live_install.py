
import os
from app_factory import create_app
from models import db, ShopifyStore, User

app = create_app()

with app.app_context():
    print("--- Verifying Live Installation ---")
    
    shop_url = "antigravity-test.myshopify.com"
    store = ShopifyStore.query.filter_by(shop_url=shop_url).first()
    
    if store:
        print(f"✅ Store Found: {store.shop_url}")
        print(f"   ID: {store.id}")
        print(f"   Active: {store.is_active}")
        print(f"   Installed At: {store.installed_at}")
        
        if store.access_token:
            print(f"✅ Access Token: Present (Starts with {store.access_token[:5]}...)")
        else:
            print("❌ Access Token: MISSING")
            
        if store.user:
            print(f"✅ Linked User: {store.user.email} (ID: {store.user.id})")
        else:
            print("❌ Linked User: MISSING")
            
    else:
        print(f"❌ Store {shop_url} NOT FOUND in database.")

    print("\n--- End Verification ---")
