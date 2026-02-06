"""
Comprehensive Shopify Connection Diagnostic
This checks EVERYTHING related to connecting a Shopify store
"""

import os
import sys

def check_environment():
    """Check environment variables"""
    print("\n" + "="*60)
    print("ENVIRONMENT VARIABLES")
    print("="*60)
    
    required_vars = [
        'SHOPIFY_API_KEY',
        'SHOPIFY_API_SECRET',
        'SHOPIFY_REDIRECT_URI',
        'DATABASE_URL',
        'SECRET_KEY',
    ]
    
    for var in required_vars:
        value = os.getenv(var, '')
        if value:
            # Mask sensitive values
            if len(value) > 10:
                display = f"{value[:4]}...{value[-4:]}"
            else:
                display = "***"
            print(f"✅ {var:25} = {display} (length: {len(value)})")
        else:
            print(f"❌ {var:25} = NOT SET")

def check_routes():
    """Check critical routes"""
    from app_factory import create_app
    
    print("\n" + "="*60)
    print("CRITICAL ROUTES")
    print("="*60)
    
    app = create_app()
    
    critical_routes = {
        '/install': 'OAuth initiation',
        '/auth/callback': 'OAuth callback',
        '/settings/shopify': 'Settings page',
        '/settings/shopify/connect': 'Manual connect',
        '/settings/shopify/disconnect': 'Disconnect',
        '/': 'Dashboard/Home',
        '/dashboard': 'Dashboard',
    }
    
    for path, description in critical_routes.items():
        found = any(str(rule) == path for rule in app.url_map.iter_rules())
        status = "✅" if found else "❌"
        print(f"{status} {path:30} - {description}")

def check_database():
    """Check database schema"""
    from app_factory import create_app
    from models import db
    from sqlalchemy import inspect
    
    print("\n" + "="*60)
    print("DATABASE SCHEMA")
    print("="*60)
    
    app = create_app()
    
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            
            # Check users table
            if 'users' in inspector.get_table_names():
                print("✅ users table exists")
                columns = [col['name'] for col in inspector.get_columns('users')]
                
                critical_columns = ['id', 'email', 'trial_started_at', 'trial_ends_at', 'is_subscribed']
                for col in critical_columns:
                    if col in columns:
                        print(f"  ✅ {col}")
                    else:
                        print(f"  ❌ {col} - MISSING!")
            else:
                print("❌ users table does NOT exist")
            
            # Check shopify_stores table
            if 'shopify_stores' in inspector.get_table_names():
                print("✅ shopify_stores table exists")
                columns = [col['name'] for col in inspector.get_columns('shopify_stores')]
                
                critical_columns = ['id', 'user_id', 'shop_url', 'access_token', 'is_active']
                for col in critical_columns:
                    if col in columns:
                        print(f"  ✅ {col}")
                    else:
                        print(f"  ❌ {col} - MISSING!")
            else:
                print("❌ shopify_stores table does NOT exist")
                
        except Exception as e:
            print(f"❌ Database check failed: {e}")

def check_oauth_config():
    """Check OAuth configuration"""
    print("\n" + "="*60)
    print("OAUTH CONFIGURATION")
    print("="*60)
    
    from config import SHOPIFY_API_KEY, SHOPIFY_API_SECRET, SHOPIFY_REDIRECT_URI
    
    print(f"API Key: {SHOPIFY_API_KEY[:4] if SHOPIFY_API_KEY else 'NOT SET'}... (len: {len(SHOPIFY_API_KEY) if SHOPIFY_API_KEY else 0})")
    print(f"API Secret: {SHOPIFY_API_SECRET[:4] if SHOPIFY_API_SECRET else 'NOT SET'}... (len: {len(SHOPIFY_API_SECRET) if SHOPIFY_API_SECRET else 0})")
    print(f"Redirect URI: {SHOPIFY_REDIRECT_URI}")
    
    # Check if they're valid
    if SHOPIFY_API_KEY and len(SHOPIFY_API_KEY) >= 32:
        print("✅ API Key looks valid")
    else:
        print("❌ API Key is too short or missing")
    
    if SHOPIFY_API_SECRET and len(SHOPIFY_API_SECRET) >= 32:
        print("✅ API Secret looks valid")
    else:
        print("❌ API Secret is too short or missing")
    
    if SHOPIFY_REDIRECT_URI and 'employeesuite-production.onrender.com' in SHOPIFY_REDIRECT_URI:
        print("✅ Redirect URI looks correct")
    else:
        print("❌ Redirect URI might be wrong")

def check_shopify_app_toml():
    """Check shopify.app.toml configuration"""
    print("\n" + "="*60)
    print("SHOPIFY.APP.TOML")
    print("="*60)
    
    try:
        with open('shopify.app.toml', 'r') as f:
            content = f.read()
            
        # Check critical settings
        if 'employeesuite-production.onrender.com' in content:
            print("✅ Production URL found in config")
        else:
            print("❌ Production URL NOT found in config")
        
        if 'embedded = true' in content:
            print("✅ Embedded mode enabled")
        else:
            print("⚠️  Embedded mode not explicitly set")
        
        if '/auth/callback' in content:
            print("✅ Callback URL configured")
        else:
            print("❌ Callback URL NOT configured")
            
    except FileNotFoundError:
        print("❌ shopify.app.toml NOT FOUND")

def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("COMPREHENSIVE SHOPIFY CONNECTION DIAGNOSTIC")
    print("="*60)
    
    try:
        check_environment()
        check_oauth_config()
        check_shopify_app_toml()
        check_routes()
        check_database()
        
        print("\n" + "="*60)
        print("DIAGNOSTIC COMPLETE")
        print("="*60)
        print("\nIf you see any ❌ marks above, those need to be fixed!")
        
    except Exception as e:
        print(f"\n❌ DIAGNOSTIC FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
