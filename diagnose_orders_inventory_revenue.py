#!/usr/bin/env python3
"""
Diagnostic script to identify why orders, inventory, and revenue reports aren't working.
"""

import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_database_connection():
    """Check if database is accessible"""
    print("=" * 60)
    print("1. Checking Database Connection...")
    print("=" * 60)
    try:
        from app import app, db
        from models import User, ShopifyStore
        
        with app.app_context():
            # Try to query users
            user_count = User.query.count()
            print(f"✅ Database connected - Found {user_count} users")
            
            # Check for stores
            store_count = ShopifyStore.query.filter_by(is_active=True).count()
            print(f"✅ Found {store_count} active Shopify stores")
            
            if store_count == 0:
                print("⚠️  WARNING: No active Shopify stores found!")
                print("   This is likely why your features aren't working.")
                print("   Users need to connect their Shopify store first.")
                return False
            
            return True
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def check_user_access():
    """Check if users have access (trial or subscription)"""
    print("\n" + "=" * 60)
    print("2. Checking User Access...")
    print("=" * 60)
    try:
        from app import app
        from models import User
        
        with app.app_context():
            users = User.query.all()
            if not users:
                print("⚠️  No users found in database")
                return False
            
            for user in users:
                has_access = user.has_access()
                trial_active = user.is_trial_active()
                is_subscribed = user.is_subscribed
                
                print(f"\nUser: {user.email}")
                print(f"  - Has Access: {'✅' if has_access else '❌'}")
                print(f"  - Trial Active: {'✅' if trial_active else '❌'}")
                print(f"  - Subscribed: {'✅' if is_subscribed else '❌'}")
                
                if not has_access:
                    print(f"  ⚠️  WARNING: User {user.email} does NOT have access!")
                    print("     This user cannot use orders/inventory/revenue features.")
            
            return True
    except Exception as e:
        print(f"❌ Error checking user access: {e}")
        return False

def check_shopify_stores():
    """Check Shopify store connections"""
    print("\n" + "=" * 60)
    print("3. Checking Shopify Store Connections...")
    print("=" * 60)
    try:
        from app import app
        from models import User, ShopifyStore
        
        with app.app_context():
            stores = ShopifyStore.query.filter_by(is_active=True).all()
            
            if not stores:
                print("❌ No active Shopify stores found!")
                print("   SOLUTION: Users need to connect their Shopify store at /settings/shopify")
                return False
            
            for store in stores:
                user = store.user
                print(f"\nStore: {store.shop_url}")
                print(f"  - User: {user.email if user else 'Unknown'}")
                print(f"  - Access Token: {'✅ Present' if store.access_token else '❌ Missing'}")
                print(f"  - Is Active: {'✅' if store.is_active else '❌'}")
                
                # Test API connection
                if store.access_token:
                    try:
                        from shopify_integration import ShopifyClient
                        client = ShopifyClient(store.shop_url, store.access_token)
                        # Try a simple API call
                        test_result = client._make_request("shop.json")
                        if "error" in test_result:
                            print(f"  ⚠️  API Error: {test_result.get('error', 'Unknown error')}")
                            if "401" in str(test_result) or "Authentication" in str(test_result):
                                print(f"     SOLUTION: Store needs to be reconnected - token expired")
                        else:
                            print(f"  ✅ API connection working")
                    except Exception as e:
                        print(f"  ⚠️  API test failed: {e}")
            
            return True
    except Exception as e:
        print(f"❌ Error checking Shopify stores: {e}")
        return False

def check_environment_variables():
    """Check required environment variables"""
    print("\n" + "=" * 60)
    print("4. Checking Environment Variables...")
    print("=" * 60)
    
    required_vars = [
        'SHOPIFY_API_KEY',
        'SHOPIFY_API_SECRET',
        'SECRET_KEY'
    ]
    
    all_present = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            print(f"✅ {var}: {masked}")
        else:
            print(f"❌ {var}: NOT SET")
            all_present = False
    
    if not all_present:
        print("\n⚠️  WARNING: Missing environment variables!")
        print("   These are required for authentication and Shopify integration.")
    
    return all_present

def check_api_endpoints():
    """Check if API endpoints are properly defined"""
    print("\n" + "=" * 60)
    print("5. Checking API Endpoints...")
    print("=" * 60)
    
    try:
        from app import app
        
        routes = []
        for rule in app.url_map.iter_rules():
            if '/api/' in rule.rule:
                routes.append(rule.rule)
        
        required_routes = [
            '/api/process_orders',
            '/api/update_inventory',
            '/api/generate_report'
        ]
        
        for route in required_routes:
            if route in routes:
                print(f"✅ {route} - Registered")
            else:
                print(f"❌ {route} - NOT FOUND")
        
        return all(route in routes for route in required_routes)
    except Exception as e:
        print(f"❌ Error checking routes: {e}")
        return False

def provide_solutions():
    """Provide solutions based on common issues"""
    print("\n" + "=" * 60)
    print("SOLUTIONS & TROUBLESHOOTING")
    print("=" * 60)
    
    print("""
Common Issues and Solutions:

1. "No Shopify store connected"
   → Go to /settings/shopify and connect your store
   → Make sure you complete the OAuth flow

2. "Authentication required" or "Subscription required"
   → Make sure you're logged in
   → Check if your trial has expired (7 days)
   → Subscribe if trial expired

3. "Shopify API error" or "Permission denied"
   → Your store connection may have expired
   → Go to /settings/shopify and reconnect your store
   → Make sure you grant all required permissions

4. "No orders found" or "No products found"
   → This is normal if your store has no orders/products
   → Check your Shopify admin to verify you have data

5. Features not working in embedded app
   → Make sure App Bridge is loaded
   → Check browser console for JavaScript errors
   → Try refreshing the page

6. Database connection errors
   → Check your DATABASE_URL environment variable
   → Make sure database is accessible
   → Check database connection pooling settings
    """)

def main():
    print("\n" + "=" * 60)
    print("DIAGNOSTIC: Orders, Inventory & Revenue Reports")
    print("=" * 60)
    print()
    
    results = {
        'database': check_database_connection(),
        'user_access': check_user_access(),
        'shopify_stores': check_shopify_stores(),
        'environment': check_environment_variables(),
        'api_endpoints': check_api_endpoints()
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_ok = all(results.values())
    
    if all_ok:
        print("✅ All checks passed!")
        print("\nIf features still don't work, check:")
        print("  - Browser console for JavaScript errors")
        print("  - Server logs for API errors")
        print("  - Network tab for failed requests")
    else:
        print("❌ Some checks failed. See details above.")
        print("\nMost common issues:")
        if not results['shopify_stores']:
            print("  → No Shopify store connected")
        if not results['user_access']:
            print("  → User doesn't have access (trial expired)")
        if not results['environment']:
            print("  → Missing environment variables")
    
    provide_solutions()

if __name__ == "__main__":
    main()

