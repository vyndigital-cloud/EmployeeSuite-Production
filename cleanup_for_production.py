#!/usr/bin/env python3
"""
Production Cleanup Script
Removes all debug code, console.log statements, and hardcoded debug endpoints
for clean production deployment.
"""

import os
import re
import sys
import shutil
from datetime import datetime

def backup_file(filepath):
    """Create backup of file before modifying"""
    backup_path = f"{filepath}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backed up: {filepath} -> {backup_path}")
    return backup_path

def clean_console_logs(content):
    """Remove console.log statements while preserving code structure"""
    # Pattern to match console.log statements (including multiline)
    patterns = [
        r'console\.log\([^)]*\);?\s*\n',  # Simple console.log
        r'console\.log\(\s*[^)]*\s*\);\s*\n',  # Console.log with whitespace
        r'console\.log\(\s*[^)]*(?:\n[^)]*)*\);\s*\n',  # Multiline console.log
    ]

    cleaned = content
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.DOTALL)

    # Clean up any remaining console references
    cleaned = re.sub(r'\s*console\.(log|warn|error|info|debug)\([^)]*\);?\s*\n', '', cleaned, flags=re.MULTILINE)

    return cleaned

def clean_debug_endpoints(content):
    """Remove hardcoded debug endpoint URLs"""
    # Remove 127.0.0.1:7242 references
    patterns = [
        r'http://127\.0\.0\.1:7242[^\s\'"]*',
        r'127\.0\.0\.1:7242',
    ]

    cleaned = content
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned)

    return cleaned

def clean_debug_logging_code(content):
    """Remove debug logging instrumentation"""
    # Remove debug log sections
    patterns = [
        r'#\s*region\s+agent\s+log.*?#\s*endregion',  # Agent log regions
        r'try:\s*\n\s*fetch\([^}]*\}\)\).*?catch\([^}]*\}\s*\n',  # Fetch debug calls
        r'debug_log\([^)]*\).*?\n',  # Python debug_log calls
    ]

    cleaned = content
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.DOTALL)

    return cleaned

def clean_python_file(filepath):
    """Clean Python file of debug code"""
    print(f"🧹 Cleaning Python file: {filepath}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_size = len(content)

        # Backup original
        backup_file(filepath)

        # Apply cleaning
        content = clean_debug_logging_code(content)
        content = clean_debug_endpoints(content)

        # Remove debug imports if they're unused
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            # Skip debug-specific imports and calls
            if any(debug_term in line.lower() for debug_term in [
                'debug_log(', 'DEBUG_LOG_PATH', '/tmp/debug.log', '.cursor/debug.log'
            ]):
                continue
            cleaned_lines.append(line)

        content = '\n'.join(cleaned_lines)

        # Write cleaned content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        new_size = len(content)
        saved_bytes = original_size - new_size

        if saved_bytes > 0:
            print(f"  ✅ Removed {saved_bytes} bytes of debug code")
        else:
            print(f"  ℹ️  No debug code found")

    except Exception as e:
        print(f"  ❌ Error cleaning {filepath}: {e}")

def clean_javascript_in_file(filepath):
    """Clean JavaScript code within Python/HTML files"""
    print(f"🧹 Cleaning JavaScript in: {filepath}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_size = len(content)

        # Backup original
        backup_file(filepath)

        # Clean JavaScript
        content = clean_console_logs(content)
        content = clean_debug_endpoints(content)
        content = clean_debug_logging_code(content)

        # Write cleaned content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        new_size = len(content)
        saved_bytes = original_size - new_size

        if saved_bytes > 0:
            print(f"  ✅ Removed {saved_bytes} bytes of debug JavaScript")
        else:
            print(f"  ℹ️  No debug JavaScript found")

    except Exception as e:
        print(f"  ❌ Error cleaning {filepath}: {e}")

def ensure_production_settings():
    """Ensure production-safe settings"""
    print("🔧 Checking production settings...")

    # Check if .env exists and has DEBUG=False
    env_file = '.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_content = f.read()

        if 'DEBUG=True' in env_content:
            print("  ⚠️  WARNING: DEBUG=True found in .env file")
            env_content = env_content.replace('DEBUG=True', 'DEBUG=False')
            with open(env_file, 'w') as f:
                f.write(env_content)
            print("  ✅ Set DEBUG=False in .env")
        elif 'DEBUG=False' in env_content:
            print("  ✅ DEBUG=False already set")
        else:
            print("  ℹ️  No DEBUG setting found in .env")
    else:
        print("  ℹ️  No .env file found")

def remove_debug_files():
    """Remove debug-specific files that shouldn't be in production"""
    debug_files = [
        'debug_utils.py',
        'test_all_functions.py',
        'export_all_logs.py',
        'diagnose.py',
        'fix_all_properly.py',
        'iframe_diagnostic.js',
        '.cursor/debug.log',
        'debug.log',
        'error.log',
    ]

    print("🗑️  Removing debug files...")

    for file_path in debug_files:
        if os.path.exists(file_path):
            try:
                if os.path.isfile(file_path):
                    backup_file(file_path)
                    os.remove(file_path)
                    print(f"  ✅ Removed: {file_path}")
                elif os.path.isdir(file_path):
                    shutil.move(file_path, f"{file_path}.backup")
                    print(f"  ✅ Moved to backup: {file_path}")
            except Exception as e:
                print(f"  ❌ Error removing {file_path}: {e}")
        else:
            print(f"  ℹ️  Not found: {file_path}")

def main():
    """Main cleanup function"""
    print("🚀 Starting Production Cleanup...")
    print("=" * 50)

    # Files that need JavaScript cleaning (contain inline JS)
    js_files = [
        'app.py',
        'fix_app_bridge.py',
        'update_button_functions.py',
    ]

    # Python files that need Python debug cleaning
    python_files = [
        'security_enhancements.py',
        'database_backup.py',
        'performance.py',
        'restore_backup.py',
        'shopify_integration.py',
        'shopify_oauth.py',
        'billing.py',
        'shopify_billing.py',
        'shopify_routes.py',
        'error_handlers.py',
        'logging_config.py',
    ]

    # Clean JavaScript in files
    print("\n📝 Cleaning JavaScript...")
    for filepath in js_files:
        if os.path.exists(filepath):
            clean_javascript_in_file(filepath)
        else:
            print(f"  ℹ️  File not found: {filepath}")

    # Clean Python files
    print("\n🐍 Cleaning Python files...")
    for filepath in python_files:
        if os.path.exists(filepath):
            clean_python_file(filepath)
        else:
            print(f"  ℹ️  File not found: {filepath}")

    # Remove debug-specific files
    remove_debug_files()

    # Ensure production settings
    ensure_production_settings()

    print("\n" + "=" * 50)
    print("✅ Production cleanup completed!")
    print("\n📋 Manual checks needed:")
    print("1. Verify all console.log statements are removed")
    print("2. Ensure DEBUG=False in production environment")
    print("3. Test app functionality after cleanup")
    print("4. Check that no hardcoded debug URLs remain")
    print("\n🔄 Note: Backup files created with timestamp suffix")

if __name__ == "__main__":
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Run cleanup
    main()
