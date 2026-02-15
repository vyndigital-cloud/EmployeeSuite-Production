import os
import sys
from sqlalchemy import text, inspect
from app_factory import create_app
from models import db, User, ShopifyStore

app = create_app()

print("--- DB PROBE STARTING ---")
print(f"DATABASE_URL: {app.config['SQLALCHEMY_DATABASE_URI']}")

with app.app_context():
    try:
        # 1. Connection Test
        print("1. Testing Connection...")
        result = db.session.execute(text("SELECT 1")).scalar()
        print(f"   [OK] Connection successful. Output: {result}")

        # 2. Schema Inspection
        print("2. Inspecting Tables...")
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"   [INFO] Tables found: {tables}")
        
        expected_tables = ['users', 'shopify_stores'] # Assuming table names based on models
        missing = [t for t in expected_tables if t not in tables]
        if missing:
             print(f"   [CRITICAL] Missing Tables: {missing}")
        else:
             print("   [OK] Core tables present.")

        # 3. Data Check
        print("3. Checking User Count...")
        user_count = db.session.query(User).count()
        print(f"   [INFO] Users in DB: {user_count}")
        
    except Exception as e:
        print(f"   [FATAL] Probe Failed: {e}")
        import traceback
        traceback.print_exc()

print("--- DB PROBE COMPLETE ---")
