#!/usr/bin/env python3
"""
Final Verification Script
Comprehensive check to ensure the app is 100% ready for production deployment
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime

class ProductionVerifier:
    def __init__(self):
        self.passed_checks = 0
        self.total_checks = 0
        self.warnings = []
        self.errors = []

    def check(self, condition, success_msg, error_msg, is_critical=True):
        """Run a check and track results"""
        self.total_checks += 1

        if condition:
            print(f"  ✅ {success_msg}")
            self.passed_checks += 1
            return True
        else:
            if is_critical:
                print(f"  ❌ {error_msg}")
                self.errors.append(error_msg)
            else:
                print(f"  ⚠️  {error_msg}")
                self.warnings.append(error_msg)
            return False

    def info(self, message):
        """Display info message"""
        print(f"  ℹ️  {message}")

    def verify_file_structure(self):
        """Verify all required files are present"""
        print("\n📁 File Structure Verification...")

        critical_files = [
            'app.py',
            'requirements.txt',
            'Procfile',
            'runtime.txt',
            'build.sh'
        ]

        important_files = [
            'shopify.app.toml',
            'app.json',
            'models.py',
            'auth.py',
            'billing.py'
        ]

        for file in critical_files:
            self.check(
                os.path.exists(file),
                f"{file} exists",
                f"Critical file missing: {file}"
            )

        for file in important_files:
            self.check(
                os.path.exists(file),
                f"{file} exists",
                f"Important file missing: {file}",
                is_critical=False
            )

        # Check directories
        dirs = ['templates', 'static']
        for directory in dirs:
            if os.path.exists(directory):
                file_count = len(os.listdir(directory))
                self.info(f"{directory}/ directory has {file_count} files")

    def verify_python_syntax(self):
        """Verify Python files have correct syntax"""
        print("\n🐍 Python Syntax Verification...")

        python_files = [f for f in os.listdir('.') if f.endswith('.py')]
        syntax_errors = []

        for file in python_files:
            try:
                result = subprocess.run(
                    ['python3', '-m', 'py_compile', file],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.passed_checks += 1
                else:
                    syntax_errors.append(f"{file}: {result.stderr}")
                    self.errors.append(f"Syntax error in {file}")

                self.total_checks += 1

            except Exception as e:
                syntax_errors.append(f"{file}: {e}")
                self.errors.append(f"Could not check syntax for {file}")
                self.total_checks += 1

        if not syntax_errors:
            print(f"  ✅ All {len(python_files)} Python files have valid syntax")
        else:
            for error in syntax_errors:
                print(f"  ❌ {error}")

    def verify_dependencies(self):
        """Verify requirements.txt is complete"""
        print("\n📦 Dependencies Verification...")

        if not os.path.exists('requirements.txt'):
            self.check(False, "", "requirements.txt missing")
            return

        with open('requirements.txt', 'r') as f:
            requirements = f.read().lower()

        critical_packages = [
            'flask',
            'gunicorn',
            'sqlalchemy',
            'psycopg2-binary',
            'flask-login',
            'werkzeug'
        ]

        for package in critical_packages:
            self.check(
                package in requirements,
                f"{package} in requirements",
                f"Missing critical package: {package}"
            )

        # Count total packages
        package_count = len([line for line in requirements.split('\n') if line.strip() and not line.startswith('#')])
        self.info(f"Total packages in requirements.txt: {package_count}")

    def verify_configuration_files(self):
        """Verify configuration files are properly formatted"""
        print("\n⚙️  Configuration Files Verification...")

        # Check Procfile
        if os.path.exists('Procfile'):
            with open('Procfile', 'r') as f:
                procfile = f.read()

            self.check(
                'gunicorn' in procfile and 'app:app' in procfile,
                "Procfile has correct gunicorn configuration",
                "Procfile format incorrect"
            )

        # Check runtime.txt
        if os.path.exists('runtime.txt'):
            with open('runtime.txt', 'r') as f:
                runtime = f.read().strip()

            self.check(
                runtime.startswith('python-3.'),
                f"Python runtime specified: {runtime}",
                "Invalid Python runtime specification"
            )

        # Check app.json
        if os.path.exists('app.json'):
            try:
                with open('app.json', 'r') as f:
                    app_config = json.load(f)

                self.check(
                    app_config.get('name'),
                    "app.json has name field",
                    "app.json missing name"
                )

                self.check(
                    app_config.get('application_url'),
                    "app.json has application_url",
                    "app.json missing application_url"
                )

                self.check(
                    app_config.get('embedded') == True,
                    "app.json configured for embedded app",
                    "app.json not configured for embedded app"
                )

            except json.JSONDecodeError:
                self.check(False, "", "app.json is not valid JSON")

        # Check shopify.app.toml
        if os.path.exists('shopify.app.toml'):
            with open('shopify.app.toml', 'r') as f:
                toml_content = f.read()

            self.check(
                'client_id' in toml_content,
                "Shopify app has client_id",
                "Shopify app missing client_id"
            )

            self.check(
                'application_url' in toml_content,
                "Shopify app has application_url",
                "Shopify app missing application_url"
            )

            self.check(
                'embedded = true' in toml_content,
                "Shopify app configured as embedded",
                "Shopify app not configured as embedded"
            )

    def verify_security_settings(self):
        """Verify security configurations"""
        print("\n🔐 Security Verification...")

        # Check for hardcoded secrets (basic check)
        security_issues = []

        files_to_check = ['app.py', 'auth.py', 'billing.py']
        dangerous_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'key\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
        ]

        for file in files_to_check:
            if os.path.exists(file):
                with open(file, 'r') as f:
                    content = f.read()

                for pattern in dangerous_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        security_issues.append(f"Potential hardcoded secret in {file}")

        self.check(
            len(security_issues) == 0,
            "No hardcoded secrets found",
            f"Security issues found: {len(security_issues)}",
            is_critical=False
        )

        # Check for debug code removal
        debug_patterns = [
            'console.log',
            'debug_log(',
            '127.0.0.1:7242',
            'DEBUG=True'
        ]

        debug_found = []
        for file in ['app.py']:
            if os.path.exists(file):
                with open(file, 'r') as f:
                    content = f.read()

                for pattern in debug_patterns:
                    if pattern in content:
                        debug_found.append(f"{pattern} in {file}")

        self.check(
            len(debug_found) == 0,
            "Debug code successfully removed",
            f"Debug code still present: {len(debug_found)} instances",
            is_critical=False
        )

    def verify_database_configuration(self):
        """Verify database setup"""
        print("\n🗄️  Database Configuration Verification...")

        if os.path.exists('models.py'):
            with open('models.py', 'r') as f:
                models_content = f.read()

            self.check(
                'SQLAlchemy' in models_content,
                "SQLAlchemy models configured",
                "SQLAlchemy not found in models.py"
            )

            self.check(
                'postgresql' in models_content.lower() or 'postgres' in models_content.lower(),
                "PostgreSQL configuration found",
                "PostgreSQL configuration not found",
                is_critical=False
            )

        # Check for migration files
        migration_files = [f for f in os.listdir('.') if f.startswith('migrate_')]
        if migration_files:
            self.info(f"Found {len(migration_files)} migration files")

    def verify_shopify_integration(self):
        """Verify Shopify integration setup"""
        print("\n🛍️  Shopify Integration Verification...")

        shopify_files = ['shopify_oauth.py', 'shopify_integration.py', 'shopify_routes.py']

        for file in shopify_files:
            self.check(
                os.path.exists(file),
                f"{file} exists",
                f"Shopify file missing: {file}",
                is_critical=False
            )

        # Check API version consistency
        if os.path.exists('shopify_integration.py'):
            with open('shopify_integration.py', 'r') as f:
                content = f.read()

            self.check(
                '2025-10' in content,
                "Using current Shopify API version (2025-10)",
                "Outdated Shopify API version",
                is_critical=False
            )

        # Check webhook configuration
        webhook_files = [f for f in os.listdir('.') if 'webhook' in f.lower()]
        if webhook_files:
            self.info(f"Found {len(webhook_files)} webhook-related files")

    def verify_deployment_readiness(self):
        """Final deployment readiness check"""
        print("\n🚀 Deployment Readiness Check...")

        # File size check
        if os.path.exists('app.py'):
            app_size = os.path.getsize('app.py')
            self.check(
                app_size > 1000,  # At least 1KB
                f"Main app file size: {app_size:,} bytes",
                "Main app file suspiciously small"
            )

        # Build script check
        if os.path.exists('build.sh'):
            with open('build.sh', 'r') as f:
                build_script = f.read()

            self.check(
                'pip install' in build_script,
                "Build script installs dependencies",
                "Build script missing pip install"
            )

            # Check if build.sh is executable
            is_executable = os.access('build.sh', os.X_OK)
            self.check(
                is_executable,
                "build.sh is executable",
                "build.sh is not executable",
                is_critical=False
            )

        # Environment variables documentation
        env_vars_documented = False
        readme_files = [f for f in os.listdir('.') if f.lower().startswith('readme')]

        for readme in readme_files:
            try:
                with open(readme, 'r') as f:
                    content = f.read().lower()
                if 'environment' in content and 'variable' in content:
                    env_vars_documented = True
                    break
            except:
                pass

        if env_vars_documented:
            self.info("Environment variables documented")
        else:
            self.warnings.append("Environment variables not documented")

    def generate_report(self):
        """Generate final verification report"""
        print("\n" + "="*60)
        print("📊 FINAL VERIFICATION REPORT")
        print("="*60)

        success_rate = (self.passed_checks / self.total_checks) * 100 if self.total_checks > 0 else 0

        print(f"✅ Passed: {self.passed_checks}/{self.total_checks} ({success_rate:.1f}%)")
        print(f"❌ Errors: {len(self.errors)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")

        if self.errors:
            print(f"\n❌ CRITICAL ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"   {i}. {warning}")

        print("\n" + "="*60)

        if len(self.errors) == 0:
            print("🎉 READY FOR PRODUCTION DEPLOYMENT!")
            print("✅ All critical checks passed")
            if self.warnings:
                print("⚠️  Some warnings present but not blocking")
        else:
            print("🚫 NOT READY FOR DEPLOYMENT")
            print(f"❌ {len(self.errors)} critical error(s) must be fixed")

        print("="*60)

        return len(self.errors) == 0

def main():
    """Run complete verification"""
    print("🔍 PRODUCTION DEPLOYMENT VERIFICATION")
    print("="*60)
    print(f"📅 Verification Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    verifier = ProductionVerifier()

    # Run all verification checks
    verifier.verify_file_structure()
    verifier.verify_python_syntax()
    verifier.verify_dependencies()
    verifier.verify_configuration_files()
    verifier.verify_security_settings()
    verifier.verify_database_configuration()
    verifier.verify_shopify_integration()
    verifier.verify_deployment_readiness()

    # Generate final report
    is_ready = verifier.generate_report()

    if is_ready:
        print("\n🎯 NEXT STEPS:")
        print("1. Push code to your Git repository")
        print("2. Connect repository to Render")
        print("3. Configure environment variables in Render")
        print("4. Deploy and monitor build logs")
        print("5. Update Shopify app URLs after deployment")

        print("\n🔗 QUICK LINKS:")
        print("• Render Dashboard: https://render.com/dashboard")
        print("• Shopify Partners: https://partners.shopify.com")

        sys.exit(0)
    else:
        print("\n🛠️  Please fix the critical errors above before deploying.")
        sys.exit(1)

if __name__ == "__main__":
    main()
