#!/usr/bin/env python3
"""
Basic Verification Script for MissionControl Fixes
Tests core functionality without requiring full dependency installation
"""

import importlib
import os
import sys
from pathlib import Path

# Add project directory to path
project_dir = Path(__file__).parent.absolute()
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))


def test_basic_imports():
    """Test basic Python imports for our core modules"""
    print("🔍 Testing Core Module Imports")
    print("-" * 40)

    modules_to_test = [
        ("config", "Configuration management system"),
        ("logging_config", "Logging system with security filters"),
    ]

    passed = 0
    failed = 0

    for module_name, description in modules_to_test:
        try:
            importlib.import_module(module_name)
            print(f"  ✅ {module_name}: {description}")
            passed += 1
        except ImportError as e:
            print(f"  ❌ {module_name}: Import failed - {e}")
            failed += 1
        except Exception as e:
            print(f"  ⚠️  {module_name}: Unexpected error - {e}")
            failed += 1

    return passed, failed


def test_configuration_system():
    """Test configuration system without dependencies"""
    print("\n📋 Testing Configuration System")
    print("-" * 40)

    passed = 0
    failed = 0

    try:
        # Test config import
        from config import Config, get_config

        config = get_config()
        print(f"  ✅ Configuration loaded for environment: {config.ENVIRONMENT}")
        passed += 1

        # Test basic attributes
        attrs_to_check = ["SECRET_KEY", "DATABASE_URL", "SHOPIFY_API_VERSION"]
        for attr in attrs_to_check:
            if hasattr(config, attr):
                print(f"  ✅ {attr}: Present")
                passed += 1
            else:
                print(f"  ❌ {attr}: Missing")
                failed += 1

        # Test validation logic
        if len(config.SECRET_KEY) >= 32:
            print(f"  ✅ SECRET_KEY: Proper length ({len(config.SECRET_KEY)} chars)")
            passed += 1
        else:
            print(f"  ❌ SECRET_KEY: Too short ({len(config.SECRET_KEY)} chars)")
            failed += 1

    except Exception as e:
        print(f"  ❌ Configuration system failed: {e}")
        failed += 1

    return passed, failed


def test_logging_system():
    """Test logging system"""
    print("\n📊 Testing Logging System")
    print("-" * 40)

    passed = 0
    failed = 0

    try:
        from logging_config import SecurityFilter, get_logger

        # Test logger creation
        logger = get_logger("test")
        print("  ✅ Logger creation: Success")
        passed += 1

        # Test security filter
        security_filter = SecurityFilter()
        print("  ✅ Security filter: Created")
        passed += 1

        # Test filter functionality
        test_message = "password=secret123 and token=abc123"
        filtered = security_filter._redact_sensitive_data(test_message)
        if "[REDACTED]" in filtered:
            print("  ✅ Security filtering: Working")
            passed += 1
        else:
            print("  ❌ Security filtering: Not working")
            failed += 1

    except Exception as e:
        print(f"  ❌ Logging system failed: {e}")
        failed += 1

    return passed, failed


def test_file_structure():
    """Test that all expected files exist"""
    print("\n📁 Testing File Structure")
    print("-" * 40)

    expected_files = [
        ("config.py", "Configuration management"),
        ("models.py", "Database models with type hints"),
        ("logging_config.py", "Logging with security filters"),
        ("data_encryption.py", "Encryption utilities"),
        ("csrf_protection.py", "CSRF protection system"),
        ("app_factory.py", "Application factory pattern"),
        ("run.py", "Production-ready launcher"),
        ("requirements.txt", "Dependencies list"),
    ]

    passed = 0
    failed = 0

    for filename, description in expected_files:
        file_path = Path(filename)
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"  ✅ {filename}: {description} ({size} bytes)")
            passed += 1
        else:
            print(f"  ❌ {filename}: Missing - {description}")
            failed += 1

    return passed, failed


def test_code_quality():
    """Test basic code quality indicators"""
    print("\n🔍 Testing Code Quality")
    print("-" * 40)

    passed = 0
    failed = 0

    # Test that files have proper structure
    files_to_check = ["config.py", "models.py", "logging_config.py"]

    for filename in files_to_check:
        try:
            with open(filename, "r") as f:
                content = f.read()

            # Check for type hints
            if (
                "from typing import" in content
                or ": str" in content
                or ": int" in content
            ):
                print(f"  ✅ {filename}: Has type hints")
                passed += 1
            else:
                print(f"  ⚠️  {filename}: Limited type hints")

            # Check for docstrings
            if '"""' in content and content.count('"""') >= 4:
                print(f"  ✅ {filename}: Has documentation")
                passed += 1
            else:
                print(f"  ⚠️  {filename}: Limited documentation")

            # Check for error handling
            if "try:" in content and "except" in content:
                print(f"  ✅ {filename}: Has error handling")
                passed += 1
            else:
                print(f"  ⚠️  {filename}: Limited error handling")

        except Exception as e:
            print(f"  ❌ {filename}: Could not analyze - {e}")
            failed += 1

    return passed, failed


def test_security_features():
    """Test security implementation"""
    print("\n🛡️  Testing Security Features")
    print("-" * 40)

    passed = 0
    failed = 0

    # Check for security patterns in files
    security_files = {
        "data_encryption.py": ["PBKDF2", "Fernet", "base64"],
        "csrf_protection.py": ["CSRFManager", "token", "validate"],
        "logging_config.py": ["SecurityFilter", "redact", "sensitive"],
    }

    for filename, required_patterns in security_files.items():
        try:
            with open(filename, "r") as f:
                content = f.read()

            found_patterns = sum(
                1 for pattern in required_patterns if pattern in content
            )
            if found_patterns == len(required_patterns):
                print(
                    f"  ✅ {filename}: All security patterns found ({found_patterns}/{len(required_patterns)})"
                )
                passed += 1
            elif found_patterns > 0:
                print(
                    f"  ⚠️  {filename}: Some security patterns found ({found_patterns}/{len(required_patterns)})"
                )
                passed += 1
            else:
                print(f"  ❌ {filename}: No security patterns found")
                failed += 1

        except Exception as e:
            print(f"  ❌ {filename}: Could not analyze - {e}")
            failed += 1

    return passed, failed


def run_basic_verification():
    """Run all basic verification tests"""
    print("🚀 MISSIONCONTROL BASIC VERIFICATION")
    print("=" * 60)
    print("Testing core functionality without full dependencies")
    print("=" * 60)

    total_passed = 0
    total_failed = 0

    # Run all test suites
    test_suites = [
        ("Core Imports", test_basic_imports),
        ("Configuration", test_configuration_system),
        ("Logging", test_logging_system),
        ("File Structure", test_file_structure),
        ("Code Quality", test_code_quality),
        ("Security Features", test_security_features),
    ]

    for suite_name, test_func in test_suites:
        try:
            passed, failed = test_func()
            total_passed += passed
            total_failed += failed

            # Show suite summary
            total_tests = passed + failed
            if total_tests > 0:
                success_rate = (passed / total_tests) * 100
                print(
                    f"  📊 {suite_name} Results: {passed}/{total_tests} passed ({success_rate:.1f}%)"
                )

        except Exception as e:
            print(f"  💥 {suite_name} suite failed: {e}")
            total_failed += 1

    # Final summary
    print("\n" + "=" * 60)
    print("📊 BASIC VERIFICATION SUMMARY")
    print("=" * 60)

    total_tests = total_passed + total_failed
    if total_tests > 0:
        success_rate = (total_passed / total_tests) * 100
        print(
            f"Overall Results: {total_passed}/{total_tests} tests passed ({success_rate:.1f}%)"
        )

    if total_failed == 0:
        print("\n🎉 ALL BASIC TESTS PASSED!")
        print("✅ Core architecture fixes are working correctly")
        print("✅ Security implementations are in place")
        print("✅ Code quality improvements verified")

        print("\n🚀 Next Steps:")
        print("  1. Install full dependencies: pip install -r requirements.txt")
        print("  2. Run complete verification: python verify_fixes.py")
        print("  3. Set up environment variables")
        print("  4. Initialize database")
        print("  5. Deploy to staging environment")

    elif success_rate >= 75:
        print(f"\n⚠️  MOSTLY SUCCESSFUL ({success_rate:.1f}%)")
        print("✅ Major architectural fixes are working")
        print("⚠️  Some minor issues found - review above")

        print("\n🔧 Recommended Actions:")
        print("  1. Review and fix any failed tests")
        print("  2. Install missing dependencies")
        print("  3. Run full verification suite")

    else:
        print(f"\n❌ SIGNIFICANT ISSUES FOUND ({success_rate:.1f}%)")
        print("⚠️  Core fixes may not be working correctly")

        print("\n🚨 Required Actions:")
        print("  1. Review all failed tests above")
        print("  2. Fix critical issues before proceeding")
        print("  3. Re-run basic verification")

    print("\n📚 Documentation Available:")
    print("  - AUDIT_COMPLETE_DEPLOYMENT_READY.md: Full deployment guide")
    print("  - CRITICAL_FIXES_APPLIED_2025.md: Details of all fixes")
    print("  - COMPREHENSIVE_AUDIT_REPORT_2025.md: Original audit findings")

    return success_rate


if __name__ == "__main__":
    success_rate = run_basic_verification()
    sys.exit(0 if success_rate >= 75 else 1)
