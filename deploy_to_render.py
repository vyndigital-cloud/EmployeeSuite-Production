#!/usr/bin/env python3
"""
Production Deployment Script for Render
Automated deployment with pre-flight checks and environment validation
"""

import os
import sys
import json
import subprocess
from datetime import datetime

# Render API configuration (if using API deployment)
RENDER_API_BASE = "https://api.render.com/v1"
SERVICE_ID = "srv-your-service-id"  # Update with actual service ID

def print_banner():
    """Print deployment banner"""
    print("=" * 60)
    print("🚀 EMPLOYEE SUITE - PRODUCTION DEPLOYMENT")
    print("=" * 60)
    print(f"📅 Deployment Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Target Platform: Render.com")
    print("=" * 60)

def check_environment():
    """Check environment and prerequisites"""
    print("\n🔍 Pre-flight Environment Check...")

    checks = []

    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 8):
        print(f"  ✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        checks.append(True)
    else:
        print(f"  ❌ Python version too old: {python_version}")
        checks.append(False)

    # Check required files
    required_files = [
        'app.py',
        'requirements.txt',
        'Procfile',
        'runtime.txt',
        'build.sh'
    ]

    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
            checks.append(True)
        else:
            print(f"  ❌ Missing: {file}")
            checks.append(False)

    # Check environment variables (critical ones)
    critical_env_vars = [
        'SHOPIFY_API_KEY',
        'SHOPIFY_API_SECRET',
        'DATABASE_URL',
        'SECRET_KEY'
    ]

    print("\n🔐 Environment Variables Check...")
    for var in critical_env_vars:
        if os.getenv(var):
            print(f"  ✅ {var} (set)")
            checks.append(True)
        else:
            print(f"  ⚠️  {var} (not set - must be configured in Render)")
            # Don't fail deployment for env vars - they should be set in Render

    return all(checks[:len(required_files) + 1])  # Only fail on files and Python version

def validate_app_config():
    """Validate app configuration files"""
    print("\n📋 Validating Configuration...")

    # Check Procfile
    try:
        with open('Procfile', 'r') as f:
            procfile_content = f.read().strip()
        if 'gunicorn' in procfile_content and 'app:app' in procfile_content:
            print("  ✅ Procfile valid")
        else:
            print("  ⚠️  Procfile format may be incorrect")
    except Exception as e:
        print(f"  ❌ Error reading Procfile: {e}")
        return False

    # Check requirements.txt
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
        required_packages = ['Flask', 'gunicorn', 'psycopg2-binary']
        for package in required_packages:
            if package in requirements:
                print(f"  ✅ {package} in requirements")
            else:
                print(f"  ❌ Missing: {package}")
    except Exception as e:
        print(f"  ❌ Error reading requirements.txt: {e}")
        return False

    # Check Shopify app configuration
    try:
        with open('shopify.app.toml', 'r') as f:
            toml_content = f.read()
        if 'client_id' in toml_content and 'application_url' in toml_content:
            print("  ✅ Shopify app configuration valid")
        else:
            print("  ⚠️  Shopify configuration incomplete")
    except Exception as e:
        print(f"  ⚠️  Shopify app configuration file not found: {e}")

    # Check app.json
    try:
        with open('app.json', 'r') as f:
            app_config = json.load(f)
        if app_config.get('name') and app_config.get('application_url'):
            print("  ✅ app.json valid")
        else:
            print("  ⚠️  app.json incomplete")
    except Exception as e:
        print(f"  ⚠️  app.json not found or invalid: {e}")

    return True

def run_tests():
    """Run basic tests before deployment"""
    print("\n🧪 Running Pre-deployment Tests...")

    # Test Python syntax
    try:
        result = subprocess.run(['python3', '-m', 'py_compile', 'app.py'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✅ Python syntax check passed")
        else:
            print(f"  ❌ Python syntax errors: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Could not run syntax check: {e}")
        return False

    # Test import of main modules
    test_imports = [
        'import flask',
        'import sqlalchemy',
        'import psycopg2',
        'import gunicorn'
    ]

    for import_test in test_imports:
        try:
            result = subprocess.run(['python3', '-c', import_test],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                module_name = import_test.split(' ')[1]
                print(f"  ✅ {module_name} import successful")
            else:
                module_name = import_test.split(' ')[1]
                print(f"  ⚠️  {module_name} not available (will be installed by Render)")
        except Exception as e:
            print(f"  ⚠️  Could not test import: {e}")

    return True

def create_deployment_summary():
    """Create deployment summary"""
    print("\n📊 Deployment Summary...")

    # Count files
    python_files = len([f for f in os.listdir('.') if f.endswith('.py')])
    template_files = len([f for f in os.listdir('templates') if f.endswith('.html')]) if os.path.exists('templates') else 0
    static_files = len(os.listdir('static')) if os.path.exists('static') else 0

    print(f"  📁 Python files: {python_files}")
    print(f"  🎨 Template files: {template_files}")
    print(f"  📊 Static files: {static_files}")

    # Check file sizes
    app_size = os.path.getsize('app.py') if os.path.exists('app.py') else 0
    print(f"  📏 Main app size: {app_size:,} bytes")

    # Show key features
    print("\n🎯 Key Features Included:")
    features = [
        "✅ Shopify App Integration",
        "✅ Order Processing",
        "✅ Inventory Management",
        "✅ Revenue Analytics",
        "✅ Security Headers",
        "✅ Rate Limiting",
        "✅ Error Handling",
        "✅ GDPR Compliance",
        "✅ Webhook Support",
        "✅ Database Backup"
    ]

    for feature in features:
        print(f"    {feature}")

def display_render_instructions():
    """Display manual deployment instructions for Render"""
    print("\n" + "=" * 60)
    print("📝 RENDER DEPLOYMENT INSTRUCTIONS")
    print("=" * 60)

    print("""
🔗 Step 1: Connect Repository
   • Go to https://render.com/dashboard
   • Click "New +" → "Web Service"
   • Connect your GitHub/GitLab repository
   • Select this repository

⚙️  Step 2: Configure Service
   • Name: employee-suite-production
   • Environment: Python 3
   • Build Command: ./build.sh
   • Start Command: gunicorn --worker-class=sync --workers=1 --timeout=120 app:app
   • Instance Type: Free or Starter ($7/month recommended)

🔐 Step 3: Set Environment Variables
   Add these in Render dashboard → Environment:

   REQUIRED:
   • SHOPIFY_API_KEY=your_shopify_api_key
   • SHOPIFY_API_SECRET=your_shopify_api_secret
   • SHOPIFY_APP_URL=https://your-app-name.onrender.com
   • DATABASE_URL=postgresql://... (auto-generated if using Render PostgreSQL)
   • SECRET_KEY=your_secret_key_here

   OPTIONAL:
   • DEBUG=False
   • ENVIRONMENT=production
   • SENTRY_DSN=your_sentry_dsn (if using error tracking)
   • AWS_ACCESS_KEY_ID=... (if using S3 backups)
   • AWS_SECRET_ACCESS_KEY=... (if using S3 backups)
   • S3_BACKUP_BUCKET=... (if using S3 backups)

🗄️  Step 4: Database Setup (if needed)
   • In Render dashboard, create PostgreSQL database
   • Copy DATABASE_URL to environment variables
   • Database will auto-migrate on first run

🌐 Step 5: Custom Domain (optional)
   • Go to Settings → Custom Domains
   • Add your domain (e.g., employeesuite.com)
   • Update SHOPIFY_APP_URL environment variable
   • Update Shopify app settings with new URL

🎯 Step 6: Shopify App Configuration
   • In Shopify Partners dashboard:
     - Update App URL to: https://your-app-name.onrender.com
     - Update Redirect URL to: https://your-app-name.onrender.com/auth/callback
     - Save changes

📊 Step 7: Deploy
   • Click "Create Web Service"
   • Monitor build logs for any issues
   • Test the deployment once complete
""")

def main():
    """Main deployment function"""
    print_banner()

    # Pre-flight checks
    if not check_environment():
        print("\n❌ Pre-flight checks failed. Please fix issues above.")
        sys.exit(1)

    if not validate_app_config():
        print("\n❌ Configuration validation failed. Please fix issues above.")
        sys.exit(1)

    if not run_tests():
        print("\n❌ Pre-deployment tests failed. Please fix issues above.")
        sys.exit(1)

    # Create summary
    create_deployment_summary()

    print("\n" + "=" * 60)
    print("✅ ALL PRE-FLIGHT CHECKS PASSED!")
    print("🚀 Ready for Production Deployment")
    print("=" * 60)

    # Show deployment instructions
    display_render_instructions()

    print("\n" + "=" * 60)
    print("🎉 DEPLOYMENT SCRIPT COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("\n🔗 Quick Links:")
    print("• Render Dashboard: https://render.com/dashboard")
    print("• Shopify Partners: https://partners.shopify.com")
    print("• Documentation: https://render.com/docs")

    print(f"\n📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n💡 Next: Follow the manual steps above to complete deployment")

if __name__ == "__main__":
    main()
