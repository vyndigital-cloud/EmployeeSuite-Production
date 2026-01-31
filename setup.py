#!/usr/bin/env python3
"""
Setup Script for MissionControl Shopify App
Installs dependencies, sets up environment, and prepares application for deployment
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, description="", check=True):
    """Run a shell command and handle errors"""
    print(f"🔧 {description or command}")
    try:
        result = subprocess.run(
            command, shell=True, check=check, capture_output=True, text=True
        )
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e}")
        if e.stderr:
            print(f"   Stderr: {e.stderr.strip()}")
        return False


def check_python_version():
    """Check Python version compatibility"""
    print("🐍 Checking Python version...")

    version = sys.version_info
    if version.major != 3 or version.minor < 11:
        print(f"   ❌ Python 3.11+ required, found {version.major}.{version.minor}")
        print("   Please upgrade Python: https://www.python.org/downloads/")
        return False

    print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True


def create_virtual_environment():
    """Create virtual environment if it doesn't exist"""
    print("📦 Setting up virtual environment...")

    venv_path = Path("venv")
    if venv_path.exists():
        print("   ✅ Virtual environment already exists")
        return True

    if not run_command("python -m venv venv", "Creating virtual environment"):
        print("   ❌ Failed to create virtual environment")
        return False

    print("   ✅ Virtual environment created")
    return True


def activate_virtual_environment():
    """Get activation command for virtual environment"""
    if os.name == "nt":  # Windows
        return "venv\\Scripts\\activate"
    else:  # Unix/Linux/macOS
        return "source venv/bin/activate"


def install_dependencies():
    """Install Python dependencies"""
    print("📚 Installing dependencies...")

    # Determine pip command (use venv pip if available)
    pip_cmd = "venv/bin/pip" if os.path.exists("venv/bin/pip") else "pip"
    if os.name == "nt":  # Windows
        pip_cmd = (
            "venv\\Scripts\\pip.exe"
            if os.path.exists("venv\\Scripts\\pip.exe")
            else "pip"
        )

    # Upgrade pip first
    if not run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip"):
        print("   ⚠️  Warning: Could not upgrade pip")

    # Install from requirements.txt
    if not run_command(
        f"{pip_cmd} install -r requirements.txt", "Installing requirements"
    ):
        print("   ❌ Failed to install dependencies")
        return False

    print("   ✅ Dependencies installed successfully")
    return True


def setup_environment_file():
    """Create .env file from template"""
    print("🔧 Setting up environment configuration...")

    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        print("   ✅ .env file already exists")
        return True

    # Create basic .env file
    env_content = """# MissionControl Environment Configuration
# Copy this file to .env and update with your values

# Application Environment (development, production, testing)
ENVIRONMENT=development

# Security Keys (generate new ones for production)
SECRET_KEY=dev-secret-key-change-for-production-use-32-chars-minimum
ENCRYPTION_KEY=dev-encryption-key-change-for-production

# Database Configuration
DATABASE_URL=sqlite:///app.db

# Shopify Configuration
SHOPIFY_API_KEY=your_shopify_api_key_here
SHOPIFY_API_SECRET=your_shopify_api_secret_here
SHOPIFY_API_VERSION=2025-10
SHOPIFY_SCOPES=read_products,write_products,read_orders,write_orders,read_inventory,write_inventory

# Application URLs
APP_URL=http://localhost:5000

# Optional: Error Tracking
SENTRY_DSN=

# Optional: Email Configuration
SENDGRID_API_KEY=
FROM_EMAIL=noreply@example.com

# Optional: Stripe Configuration
STRIPE_PUBLIC_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Development Settings
DEBUG=True
LOG_LEVEL=INFO
"""

    try:
        with open(env_file, "w") as f:
            f.write(env_content)
        print("   ✅ .env file created from template")
        print("   ⚠️  IMPORTANT: Update .env file with your actual values!")
        return True
    except Exception as e:
        print(f"   ❌ Failed to create .env file: {e}")
        return False


def generate_security_keys():
    """Generate secure keys for the application"""
    print("🔐 Generating security keys...")

    try:
        import secrets

        # Generate SECRET_KEY
        secret_key = secrets.token_urlsafe(32)

        # Generate ENCRYPTION_KEY using cryptography
        from cryptography.fernet import Fernet

        encryption_key = Fernet.generate_key().decode()

        print("   ✅ Security keys generated")
        print(f"   🔑 SECRET_KEY: {secret_key}")
        print(f"   🔑 ENCRYPTION_KEY: {encryption_key}")
        print("   ⚠️  SAVE THESE KEYS SECURELY AND UPDATE YOUR .env FILE!")

        return True
    except ImportError:
        print("   ⚠️  Could not generate keys (cryptography not installed yet)")
        return False
    except Exception as e:
        print(f"   ❌ Error generating keys: {e}")
        return False


def create_directories():
    """Create necessary directories"""
    print("📁 Creating application directories...")

    directories = [
        "logs",
        "uploads",
        "instance",
        "static/css",
        "static/js",
        "templates",
    ]

    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)

    print("   ✅ Directories created")
    return True


def run_verification():
    """Run verification script if available"""
    print("🔍 Running verification tests...")

    if not Path("verify_fixes.py").exists():
        print("   ⚠️  Verification script not found, skipping tests")
        return True

    # Use venv python if available
    python_cmd = "venv/bin/python" if os.path.exists("venv/bin/python") else "python"
    if os.name == "nt":  # Windows
        python_cmd = (
            "venv\\Scripts\\python.exe"
            if os.path.exists("venv\\Scripts\\python.exe")
            else "python"
        )

    if run_command(
        f"{python_cmd} verify_fixes.py", "Running verification tests", check=False
    ):
        print("   ✅ Verification completed")
        return True
    else:
        print("   ⚠️  Some verification tests failed - check output above")
        return False


def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)

    print("\n📋 Next Steps:")
    print("1. 📝 Update .env file with your actual configuration:")
    print("   - Add your Shopify API credentials")
    print("   - Set production database URL")
    print("   - Update APP_URL for your domain")

    print("\n2. 🗄️  Set up your database:")
    if os.name == "nt":  # Windows
        print(
            '   venv\\Scripts\\python.exe -c "from app_factory import create_app; from models import init_db; app = create_app(); init_db(app)"'
        )
    else:
        print(
            '   venv/bin/python -c "from app_factory import create_app; from models import init_db; app = create_app(); init_db(app)"'
        )

    print("\n3. 🚀 Run the application:")
    activate_cmd = activate_virtual_environment()
    print(f"   {activate_cmd}")
    print("   python run.py")

    print("\n4. 🔗 Access your app:")
    print("   http://localhost:5000")

    print("\n📚 Documentation:")
    print("   - AUDIT_COMPLETE_DEPLOYMENT_READY.md - Full deployment guide")
    print("   - CRITICAL_FIXES_APPLIED_2025.md - Details of fixes applied")

    print("\n🆘 Need Help?")
    print("   - Check the logs/ directory for application logs")
    print("   - Run verify_fixes.py to test your installation")
    print("   - Review the documentation files for troubleshooting")


def main():
    """Main setup function"""
    print("🚀 MissionControl Shopify App Setup")
    print("=" * 60)
    print("This script will set up your development environment")
    print("and prepare the application for deployment.\n")

    # Change to script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    success_steps = 0
    total_steps = 7

    # Step 1: Check Python version
    if check_python_version():
        success_steps += 1
    else:
        print("❌ Setup failed: Python version incompatible")
        sys.exit(1)

    # Step 2: Create virtual environment
    if create_virtual_environment():
        success_steps += 1

    # Step 3: Install dependencies
    if install_dependencies():
        success_steps += 1

    # Step 4: Create directories
    if create_directories():
        success_steps += 1

    # Step 5: Setup environment file
    if setup_environment_file():
        success_steps += 1

    # Step 6: Generate security keys
    if generate_security_keys():
        success_steps += 1

    # Step 7: Run verification
    if run_verification():
        success_steps += 1

    # Summary
    print(f"\n📊 Setup Summary: {success_steps}/{total_steps} steps completed")

    if success_steps == total_steps:
        print_next_steps()
    elif success_steps >= total_steps - 1:
        print("\n⚠️  Setup completed with minor issues")
        print_next_steps()
    else:
        print("\n❌ Setup incomplete - please review errors above")
        print("Try running individual steps manually or check requirements")

    return success_steps == total_steps


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
