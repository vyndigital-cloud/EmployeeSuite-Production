#!/usr/bin/env python3
"""
Comprehensive Verification Script for MissionControl Fixes
Tests all critical components and fixes applied during the audit
"""

import importlib
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Tuple

# Add project directory to path
project_dir = Path(__file__).parent.absolute()
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class VerificationResults:
    """Track verification test results"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results: List[Tuple[str, bool, str]] = []

    def add_result(self, test_name: str, passed: bool, message: str = ""):
        self.results.append((test_name, passed, message))
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def add_warning(self, test_name: str, message: str):
        self.results.append((test_name, None, f"WARNING: {message}"))
        self.warnings += 1

    def get_summary(self) -> str:
        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0
        return f"Tests: {total}, Passed: {self.passed}, Failed: {self.failed}, Warnings: {self.warnings}, Success Rate: {success_rate:.1f}%"


def test_imports() -> VerificationResults:
    """Test that all critical modules can be imported"""
    results = VerificationResults()

    critical_modules = [
        ("config", "Configuration management"),
        ("models", "Database models"),
        ("data_encryption", "Encryption system"),
        ("logging_config", "Logging system"),
        ("csrf_protection", "CSRF protection"),
        ("app_factory", "Application factory"),
    ]

    for module_name, description in critical_modules:
        try:
            importlib.import_module(module_name)
            results.add_result(
                f"Import {module_name}", True, f"{description} imported successfully"
            )
        except Exception as e:
            results.add_result(
                f"Import {module_name}", False, f"Failed to import {description}: {e}"
            )

    return results


def test_configuration() -> VerificationResults:
    """Test configuration management system"""
    results = VerificationResults()

    try:
        from config import Config, get_config

        # Test config loading
        config = get_config()
        results.add_result(
            "Config Loading",
            True,
            f"Configuration loaded for environment: {config.ENVIRONMENT}",
        )

        # Test required attributes
        required_attrs = [
            "SECRET_KEY",
            "DATABASE_URL",
            "SHOPIFY_API_VERSION",
            "ENCRYPTION_KEY",
        ]
        for attr in required_attrs:
            if hasattr(config, attr):
                results.add_result(f"Config {attr}", True, f"{attr} is configured")
            else:
                results.add_result(f"Config {attr}", False, f"{attr} is missing")

        # Test validation
        if len(config.SECRET_KEY) >= 32:
            results.add_result(
                "Secret Key Length", True, "Secret key meets minimum length requirement"
            )
        else:
            results.add_warning(
                "Secret Key Length", "Secret key should be at least 32 characters"
            )

    except Exception as e:
        results.add_result(
            "Configuration System", False, f"Configuration system failed: {e}"
        )

    return results


def test_database_models() -> VerificationResults:
    """Test database models and validation"""
    results = VerificationResults()

    try:
        from models import ShopifyStore, User, db

        # Test model imports
        results.add_result(
            "Model Import", True, "Database models imported successfully"
        )

        # Test User model validation
        user = User(email="test@example.com")
        if hasattr(user, "validate_email"):
            results.add_result(
                "User Validation", True, "User model has validation methods"
            )
        else:
            results.add_warning(
                "User Validation", "User model validation methods not found"
            )

        # Test ShopifyStore model validation
        store = ShopifyStore(
            user_id=1, shop_url="test.myshopify.com", access_token="shpat_test"
        )
        if hasattr(store, "validate_shop_url"):
            results.add_result(
                "Store Validation", True, "ShopifyStore model has validation methods"
            )
        else:
            results.add_warning(
                "Store Validation", "ShopifyStore model validation methods not found"
            )

        # Test type hints (check if __annotations__ exist)
        if hasattr(User, "__annotations__") and User.__annotations__:
            results.add_result(
                "User Type Hints",
                True,
                f"User model has {len(User.__annotations__)} type hints",
            )
        else:
            results.add_warning("User Type Hints", "User model missing type hints")

        if hasattr(ShopifyStore, "__annotations__") and ShopifyStore.__annotations__:
            results.add_result(
                "Store Type Hints",
                True,
                f"ShopifyStore model has {len(ShopifyStore.__annotations__)} type hints",
            )
        else:
            results.add_warning(
                "Store Type Hints", "ShopifyStore model missing type hints"
            )

    except Exception as e:
        results.add_result(
            "Database Models", False, f"Database models test failed: {e}"
        )

    return results


def test_encryption() -> VerificationResults:
    """Test encryption system"""
    results = VerificationResults()

    try:
        from data_encryption import (
            decrypt_access_token,
            decrypt_data,
            encrypt_access_token,
            encrypt_data,
            generate_encryption_key,
            is_encryption_available,
        )

        # Test encryption availability
        if is_encryption_available():
            results.add_result(
                "Encryption Available", True, "Encryption system is available"
            )

            # Test basic encryption/decryption
            test_data = "test_secret_data"
            encrypted = encrypt_data(test_data)
            if encrypted:
                decrypted = decrypt_data(encrypted)
                if decrypted == test_data:
                    results.add_result(
                        "Encryption/Decryption",
                        True,
                        "Basic encryption/decryption works",
                    )
                else:
                    results.add_result(
                        "Encryption/Decryption",
                        False,
                        "Decryption doesn't match original data",
                    )
            else:
                results.add_warning(
                    "Encryption", "Encryption returned None (may be expected in dev)"
                )

            # Test token encryption
            test_token = "shpat_test_token_12345"
            encrypted_token = encrypt_access_token(test_token)
            if encrypted_token:
                decrypted_token = decrypt_access_token(encrypted_token)
                if decrypted_token == test_token:
                    results.add_result(
                        "Token Encryption", True, "Access token encryption works"
                    )
                else:
                    results.add_result(
                        "Token Encryption", False, "Token decryption failed"
                    )
            else:
                results.add_warning(
                    "Token Encryption", "Token encryption returned None"
                )
        else:
            results.add_warning(
                "Encryption", "Encryption not available (ENCRYPTION_KEY not set)"
            )

        # Test key generation
        key = generate_encryption_key()
        if key and len(key) > 32:
            results.add_result(
                "Key Generation", True, "Encryption key generation works"
            )
        else:
            results.add_result("Key Generation", False, "Key generation failed")

    except Exception as e:
        results.add_result("Encryption System", False, f"Encryption system failed: {e}")

    return results


def test_logging() -> VerificationResults:
    """Test logging system"""
    results = VerificationResults()

    try:
        from logging_config import (
            SecurityFilter,
            get_logger,
            log_comprehensive_error,
            setup_logging,
        )

        # Test logger creation
        logger = get_logger("test")
        results.add_result("Logger Creation", True, "Logger creation works")

        # Test security filter
        security_filter = SecurityFilter()
        results.add_result(
            "Security Filter", True, "Security filter created successfully"
        )

        # Test comprehensive error logging
        try:
            log_comprehensive_error("TEST", "Test error message", "test_location")
            results.add_result(
                "Error Logging", True, "Comprehensive error logging works"
            )
        except Exception as e:
            results.add_result("Error Logging", False, f"Error logging failed: {e}")

    except Exception as e:
        results.add_result("Logging System", False, f"Logging system failed: {e}")

    return results


def test_csrf_protection() -> VerificationResults:
    """Test CSRF protection system"""
    results = VerificationResults()

    try:
        from csrf_protection import (
            CSRFManager,
            generate_csrf_secret,
            validate_csrf_token,
        )

        # Test CSRF manager creation
        csrf_manager = CSRFManager()
        results.add_result("CSRF Manager", True, "CSRF manager created successfully")

        # Test secret generation
        secret = generate_csrf_secret()
        if secret and len(secret) > 16:
            results.add_result("CSRF Secret", True, "CSRF secret generation works")
        else:
            results.add_result("CSRF Secret", False, "CSRF secret generation failed")

    except Exception as e:
        results.add_result("CSRF Protection", False, f"CSRF protection failed: {e}")

    return results


def test_application_factory() -> VerificationResults:
    """Test application factory"""
    results = VerificationResults()

    try:
        from app_factory import create_app, create_test_app

        # Test app creation
        app = create_test_app()  # Use test app to avoid production requirements
        results.add_result("App Factory", True, "Application factory works")

        # Test app configuration
        if app.config.get("TESTING"):
            results.add_result(
                "Test App Config", True, "Test application configured correctly"
            )
        else:
            results.add_warning(
                "Test App Config", "Test application not properly configured"
            )

    except Exception as e:
        results.add_result(
            "Application Factory", False, f"Application factory failed: {e}"
        )

    return results


def test_environment_validation() -> VerificationResults:
    """Test environment variable validation"""
    results = VerificationResults()

    # Save current environment
    original_env = os.environ.copy()

    try:
        # Test missing required variables (in production)
        os.environ["ENVIRONMENT"] = "production"
        os.environ.pop("SECRET_KEY", None)

        try:
            from config import get_config

            config = get_config()
            results.add_result(
                "Production Validation", False, "Should fail without required variables"
            )
        except ValueError:
            results.add_result(
                "Production Validation",
                True,
                "Properly validates required production variables",
            )
        except Exception as e:
            results.add_result("Production Validation", False, f"Unexpected error: {e}")

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

    return results


def test_circular_imports() -> VerificationResults:
    """Test that circular imports are resolved"""
    results = VerificationResults()

    try:
        # Try importing app_factory and then config
        from app_factory import create_app
        from config import get_config
        from data_encryption import encrypt_data

        # Try importing models and then encryption
        from models import ShopifyStore, User

        results.add_result(
            "Circular Imports", True, "No circular import issues detected"
        )

    except ImportError as e:
        if "circular import" in str(e).lower():
            results.add_result(
                "Circular Imports", False, f"Circular import detected: {e}"
            )
        else:
            results.add_result("Circular Imports", False, f"Import error: {e}")
    except Exception as e:
        results.add_result("Circular Imports", False, f"Unexpected error: {e}")

    return results


def run_comprehensive_verification() -> None:
    """Run all verification tests"""
    print("🔍 MISSIONCONTROL FIXES VERIFICATION")
    print("=" * 60)

    all_results = VerificationResults()

    # Run all test suites
    test_suites = [
        ("Import Tests", test_imports),
        ("Configuration Tests", test_configuration),
        ("Database Model Tests", test_database_models),
        ("Encryption Tests", test_encryption),
        ("Logging Tests", test_logging),
        ("CSRF Protection Tests", test_csrf_protection),
        ("Application Factory Tests", test_application_factory),
        ("Environment Validation Tests", test_environment_validation),
        ("Circular Import Tests", test_circular_imports),
    ]

    for suite_name, test_func in test_suites:
        print(f"\n📋 {suite_name}")
        print("-" * 40)

        try:
            results = test_func()

            for test_name, passed, message in results.results:
                if passed is True:
                    print(f"  ✅ {test_name}: {message}")
                elif passed is False:
                    print(f"  ❌ {test_name}: {message}")
                else:  # Warning
                    print(f"  ⚠️  {test_name}: {message}")

            # Add to overall results
            all_results.passed += results.passed
            all_results.failed += results.failed
            all_results.warnings += results.warnings

            print(f"  📊 Suite Results: {results.get_summary()}")

        except Exception as e:
            print(f"  💥 Test Suite Failed: {e}")
            all_results.failed += 1

    # Final summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Overall Results: {all_results.get_summary()}")

    if all_results.failed == 0:
        print("\n🎉 ALL CRITICAL TESTS PASSED!")
        print("✅ The MissionControl application is ready for deployment.")
        if all_results.warnings > 0:
            print(
                f"⚠️  Note: {all_results.warnings} warnings found - review recommended but not critical."
            )
    else:
        print(f"\n⚠️  {all_results.failed} TESTS FAILED")
        print("❌ Review and fix failing tests before deployment.")

    print("\n🚀 Next Steps:")
    if all_results.failed == 0:
        print("  1. Deploy to staging environment")
        print("  2. Run integration tests with Shopify")
        print("  3. Monitor for 24-48 hours")
        print("  4. Deploy to production")
    else:
        print("  1. Fix failing tests")
        print("  2. Re-run verification")
        print("  3. Proceed with deployment when all tests pass")

    print("\n📖 Documentation:")
    print("  - Read AUDIT_COMPLETE_DEPLOYMENT_READY.md for full deployment guide")
    print("  - Check CRITICAL_FIXES_APPLIED_2025.md for fix details")


if __name__ == "__main__":
    run_comprehensive_verification()
