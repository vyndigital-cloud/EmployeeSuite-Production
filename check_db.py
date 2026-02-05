
import sys
import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

print("--- DATABASE DIAGNOSTIC ---")

# Setup minimal app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

try:
    with app.app_context():
        print("Attempting to connect to database...")
        db.engine.connect()
        print("✅ Connection Successful")
        
        print("Attempting to import models...")
        from models import User, ShopifyStore
        print("✅ Models Imported")
        
        print("Attempting to create tables...")
        db.create_all()
        print("✅ Tables Created/Verified")
        
        user_count = User.query.count()
        print(f"ℹ️  User Count: {user_count}")
        
except Exception as e:
    print(f"\n❌ FATAL DATABASE ERROR: {str(e)}")
    sys.exit(1)

print("\nSUCCESS: Database checked.")
sys.exit(0)
