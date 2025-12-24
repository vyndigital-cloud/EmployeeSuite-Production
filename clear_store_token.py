#!/usr/bin/env python3
"""
Script to manually clear access_token for a Shopify store
Usage: python clear_store_token.py <shop_url>
Example: python clear_store_token.py testsuite-dev.myshopify.com
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, ShopifyStore

def clear_store_token(shop_url):
    """Clear access_token for a specific store"""
    with app.app_context():
        # Find the store
        store = ShopifyStore.query.filter_by(shop_url=shop_url).first()
        
        if not store:
            print(f"❌ Store '{shop_url}' not found in database")
            return False
        
        print(f"📦 Found store: {store.shop_url}")
        print(f"   User ID: {store.user_id}")
        print(f"   Is Active: {store.is_active}")
        print(f"   Current token: {store.access_token[:20] + '...' if store.access_token and len(store.access_token) > 20 else 'EMPTY'}")
        
        # Use the disconnect method to properly clear everything
        store.disconnect()
        db.session.commit()
        
        # Verify it's cleared
        db.session.refresh(store)
        if not store.access_token or store.access_token.strip() == '':
            print(f"✅ Successfully cleared access_token for {shop_url}")
            print(f"   Token is now: '{store.access_token}'")
            print(f"   Is Active: {store.is_active}")
            return True
        else:
            print(f"❌ Failed to clear token - still has value: {store.access_token[:20]}...")
            return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python clear_store_token.py <shop_url>")
        print("Example: python clear_store_token.py testsuite-dev.myshopify.com")
        sys.exit(1)
    
    shop_url = sys.argv[1].strip()
    # Normalize shop URL
    shop_url = shop_url.replace('https://', '').replace('http://', '').replace('www.', '')
    
    success = clear_store_token(shop_url)
    sys.exit(0 if success else 1)
