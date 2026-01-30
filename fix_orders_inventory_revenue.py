#!/usr/bin/env python3
"""
Fix script for orders, inventory, and revenue report issues.
"""

import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_invalid_shopify_stores():
    """Fix invalid Shopify store URLs"""
    print("=" * 60)
    print("Fixing Invalid Shopify Store URLs...")
    print("=" * 60)
    
    try:
        from app import app, db
        from models import ShopifyStore
        
        with app.app_context():
            # Find stores with invalid URLs (localhost, 127.0.0.1, etc.)
            invalid_stores = ShopifyStore.query.filter(
                (ShopifyStore.shop_url.like('http://127.0.0.1%')) |
                (ShopifyStore.shop_url.like('http://localhost%')) |
                (ShopifyStore.shop_url.like('https://127.0.0.1%')) |
                (ShopifyStore.shop_url.like('https://localhost%'))
            ).all()
            
            if not invalid_stores:
                print("✅ No invalid store URLs found")
                return True
            
            print(f"Found {len(invalid_stores)} invalid store(s):")
            for store in invalid_stores:
                print(f"  - {store.shop_url} (User: {store.user.email if store.user else 'Unknown'})")
                print(f"    ⚠️  This is not a valid Shopify store URL!")
                print(f"    SOLUTION: User needs to reconnect with a real Shopify store")
                print(f"    → Marking as inactive so user can reconnect...")
                
                # Mark as inactive so user can reconnect
                store.is_active = False
                db.session.commit()
                print(f"    ✅ Store marked as inactive")
            
            return True
    except Exception as e:
        print(f"❌ Error fixing stores: {e}")
        return False

def check_and_extend_trials():
    """Check trial status and provide option to extend"""
    print("\n" + "=" * 60)
    print("Checking Trial Status...")
    print("=" * 60)
    
    try:
        from app import app
        from models import User
        from datetime import datetime, timedelta
        
        with app.app_context():
            users = User.query.all()
            expired_count = 0
            
            for user in users:
                if not user.has_access():
                    expired_count += 1
                    print(f"\nUser: {user.email}")
                    print(f"  - Trial expired: {user.trial_ends_at}")
                    print(f"  - Subscribed: {user.is_subscribed}")
                    
                    # Option to extend trial for testing
                    if input(f"\nExtend trial for {user.email}? (y/n): ").lower() == 'y':
                        user.trial_ends_at = datetime.utcnow() + timedelta(days=7)
                        from app import db
                        db.session.commit()
                        print(f"  ✅ Trial extended for 7 days")
            
            if expired_count == 0:
                print("✅ All users have active access")
            
            return True
    except Exception as e:
        print(f"❌ Error checking trials: {e}")
        return False

def provide_manual_fix_instructions():
    """Provide instructions for manual fixes"""
    print("\n" + "=" * 60)
    print("MANUAL FIX INSTRUCTIONS")
    print("=" * 60)
    
    print("""
To fix your orders, inventory, and revenue reports:

1. **Fix Invalid Shopify Store Connection**
   - The store URL `http://127.0.0.1:5000` is not a valid Shopify store
   - You need to connect a REAL Shopify store
   - Steps:
     a. Log in as the user (finessor06@gmail.com)
     b. Go to /settings/shopify
     c. Click "Connect Store"
     d. Enter your REAL Shopify store URL (e.g., yourstore.myshopify.com)
     e. Complete the OAuth flow

2. **Fix User Access (Trial Expired)**
   - Some users have expired trials
   - Options:
     a. Extend trial (run this script with interactive mode)
     b. Subscribe the user
     c. Manually update trial_ends_at in database

3. **Set Environment Variables**
   - Set SECRET_KEY in your environment
   - This is required for secure sessions
   - Example: export SECRET_KEY="your-secret-key-here"

4. **Test the Features**
   - After fixing store connection:
     a. Log in as a user with active access
     b. Make sure store is connected (valid URL)
     c. Try clicking "View Orders", "Check Inventory", "Generate Report"
     d. Check browser console for any JavaScript errors
    """)

def main():
    print("\n" + "=" * 60)
    print("FIX: Orders, Inventory & Revenue Reports")
    print("=" * 60)
    print()
    
    # Fix invalid store URLs
    fix_invalid_shopify_stores()
    
    # Check trials (interactive)
    if '--extend-trials' in sys.argv:
        check_and_extend_trials()
    
    provide_manual_fix_instructions()
    
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("""
1. Connect a REAL Shopify store:
   - Log in → Go to /settings/shopify → Connect Store
   - Use a real Shopify store URL (not localhost)

2. Make sure you have active access:
   - Check if trial is active or subscribe
   - Users with expired trials cannot use features

3. Test the features:
   - View Orders
   - Check Inventory  
   - Generate Report

4. If still not working:
   - Check browser console for errors
   - Check server logs
   - Verify store has orders/products in Shopify admin
    """)

if __name__ == "__main__":
    main()










