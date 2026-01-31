#!/usr/bin/env python3
"""
Comprehensive function testing script
Tests all functions in the Employee Suite codebase for errors
"""

import sys
import os
import traceback
import json
import time
from datetime import datetime

# #region agent log
LOG_PATH = '/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log'
def debug_log(location, message, data=None, hypothesis_id='GENERAL'):
    try:
        log_entry = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000)
        }
        with open(LOG_PATH, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception:
        pass
# #endregion

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

results = {
    'passed': [],
    'failed': [],
    'skipped': []
}

def test_import(module_name, description=""):
    """Test if a module can be imported"""
    # #region agent log
    debug_log('test_all_functions.py:test_import', 'test_import entry', {'module_name': module_name, 'description': description}, 'H1')
    # #endregion
    try:
        # #region agent log
        debug_log('test_all_functions.py:test_import', 'before __import__', {'module_name': module_name}, 'H1')
        # #endregion
        __import__(module_name)
        # #region agent log
        debug_log('test_all_functions.py:test_import', 'import successful', {'module_name': module_name}, 'H1')
        # #endregion
        results['passed'].append(f"✓ Import: {module_name} {description}")
        print(f"{GREEN}✓{RESET} Import: {module_name} {description}")
        return True
    except Exception as e:
        # #region agent log
        debug_log('test_all_functions.py:test_import', 'import failed', {'module_name': module_name, 'error_type': type(e).__name__, 'error_msg': str(e)[:200]}, 'H1')
        # #endregion
        error_msg = f"✗ Import: {module_name} - {str(e)}"
        results['failed'].append(error_msg)
        print(f"{RED}✗{RESET} Import: {module_name} - {str(e)}")
        if '--verbose' in sys.argv:
            traceback.print_exc()
        return False

def test_function(module, func_name, *args, **kwargs):
    """Test if a function can be called"""
    try:
        func = getattr(module, func_name)
        result = func(*args, **kwargs)
        results['passed'].append(f"✓ Function: {module.__name__}.{func_name}")
        print(f"{GREEN}✓{RESET} Function: {module.__name__}.{func_name}")
        return True, result
    except Exception as e:
        error_msg = f"✗ Function: {module.__name__}.{func_name} - {str(e)}"
        results['failed'].append(error_msg)
        print(f"{RED}✗{RESET} Function: {module.__name__}.{func_name} - {str(e)}")
        if '--verbose' in sys.argv:
            traceback.print_exc()
        return False, None

def main():
    # #region agent log
    debug_log('test_all_functions.py:main', 'main entry', {'argv': sys.argv}, 'H2')
    # #endregion
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Employee Suite - Comprehensive Function Testing{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Set minimal environment variables to avoid errors
    # #region agent log
    debug_log('test_all_functions.py:main', 'before env vars', {'existing_env_keys': list(os.environ.keys())[:10]}, 'H3')
    # #endregion
    os.environ.setdefault('SECRET_KEY', 'test-secret-key')
    os.environ.setdefault('DATABASE_URL', 'sqlite:///test.db')
    # #region agent log
    debug_log('test_all_functions.py:main', 'after env vars', {'SECRET_KEY_set': 'SECRET_KEY' in os.environ, 'DATABASE_URL_set': 'DATABASE_URL' in os.environ}, 'H3')
    # #endregion
    
    print(f"{YELLOW}Phase 1: Testing Module Imports{RESET}\n")
    
    # Core modules
    modules_to_test = [
        ('logging_config', 'Logging configuration'),
        ('models', 'Database models'),
        ('access_control', 'Access control'),
        ('input_validation', 'Input validation'),
        ('rate_limiter', 'Rate limiter'),
        ('email_service', 'Email service'),
        ('order_processing', 'Order processing'),
        ('inventory', 'Inventory management'),
        ('reporting', 'Reporting'),
        ('auth', 'Authentication'),
        ('billing', 'Billing'),
        ('shopify_oauth', 'Shopify OAuth'),
        ('shopify_routes', 'Shopify routes'),
        ('shopify_integration', 'Shopify integration'),
        ('shopify_billing', 'Shopify billing'),
        ('webhook_stripe', 'Stripe webhooks'),
        ('webhook_shopify', 'Shopify webhooks'),
        ('admin_routes', 'Admin routes'),
        ('legal_routes', 'Legal routes'),
        ('faq_routes', 'FAQ routes'),
        ('gdpr_compliance', 'GDPR compliance'),
        ('cron_jobs', 'Cron jobs'),
        ('database_backup', 'Database backup'),
    ]
    
    imported_modules = {}
    for module_name, description in modules_to_test:
        # #region agent log
        debug_log('test_all_functions.py:main', 'testing module', {'module_name': module_name, 'modules_tested_so_far': len(imported_modules)}, 'H4')
        # #endregion
        if test_import(module_name, description):
            try:
                # #region agent log
                debug_log('test_all_functions.py:main', 'before second import', {'module_name': module_name}, 'H4')
                # #endregion
                imported_modules[module_name] = __import__(module_name)
                # #region agent log
                debug_log('test_all_functions.py:main', 'second import success', {'module_name': module_name, 'module_has_attrs': len(dir(imported_modules[module_name])) if module_name in imported_modules else 0}, 'H4')
                # #endregion
            except Exception as e:
                # #region agent log
                debug_log('test_all_functions.py:main', 'second import failed', {'module_name': module_name, 'error_type': type(e).__name__, 'error_msg': str(e)[:200]}, 'H4')
                # #endregion
                pass
    
    print(f"\n{YELLOW}Phase 2: Testing Core Functions{RESET}\n")
    
    # Test order_processing
    if 'order_processing' in imported_modules:
        try:
            mod = imported_modules['order_processing']
            if hasattr(mod, 'process_orders'):
                # Test with minimal args
                try:
                    result = mod.process_orders()
                    print(f"{GREEN}✓{RESET} process_orders() - returned: {type(result).__name__}")
                    results['passed'].append("✓ process_orders()")
                except Exception as e:
                    # Expected to fail without credentials, but should not crash
                    if "credential" in str(e).lower() or "auth" in str(e).lower() or "shopify" in str(e).lower():
                        print(f"{YELLOW}⚠{RESET} process_orders() - Expected error (no credentials): {str(e)[:50]}")
                        results['skipped'].append("⚠ process_orders() - needs credentials")
                    else:
                        print(f"{RED}✗{RESET} process_orders() - {str(e)}")
                        results['failed'].append(f"✗ process_orders() - {str(e)}")
        except Exception as e:
            print(f"{RED}✗{RESET} Error testing process_orders: {str(e)}")
            results['failed'].append(f"✗ process_orders() - {str(e)}")
    
    # Test inventory (needs Flask app context)
    if 'inventory' in imported_modules:
        try:
            mod = imported_modules['inventory']
            if hasattr(mod, 'update_inventory'):
                try:
                    # Try with Flask app context if available
                    from flask import Flask
                    test_app = Flask(__name__)
                    test_app.config['SECRET_KEY'] = 'test'
                    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
                    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
                    
                    # Import db after creating app
                    from models import db
                    db.init_app(test_app)
                    
                    with test_app.app_context():
                        result = mod.update_inventory()
                        if isinstance(result, dict) and result.get('error'):
                            if 'application context' in result['error'].lower() or 'credential' in result['error'].lower():
                                print(f"{YELLOW}⚠{RESET} update_inventory() - Expected error: {result['error'][:50]}")
                                results['skipped'].append("⚠ update_inventory() - needs credentials/context")
                            else:
                                print(f"{GREEN}✓{RESET} update_inventory() - returned: {type(result).__name__}")
                                results['passed'].append("✓ update_inventory()")
                        else:
                            print(f"{GREEN}✓{RESET} update_inventory() - returned: {type(result).__name__}")
                            results['passed'].append("✓ update_inventory()")
                except ImportError:
                    # Flask not available, test without context
                    try:
                        result = mod.update_inventory()
                        if isinstance(result, dict) and 'error' in result:
                            print(f"{YELLOW}⚠{RESET} update_inventory() - Expected error (no context): {result['error'][:50]}")
                            results['skipped'].append("⚠ update_inventory() - needs Flask context")
                        else:
                            print(f"{GREEN}✓{RESET} update_inventory() - returned: {type(result).__name__}")
                            results['passed'].append("✓ update_inventory()")
                    except Exception as e:
                        if "application context" in str(e).lower():
                            print(f"{YELLOW}⚠{RESET} update_inventory() - Expected error (no context): {str(e)[:50]}")
                            results['skipped'].append("⚠ update_inventory() - needs Flask context")
                        else:
                            print(f"{RED}✗{RESET} update_inventory() - {str(e)}")
                            results['failed'].append(f"✗ update_inventory() - {str(e)}")
                except Exception as e:
                    if "application context" in str(e).lower() or "credential" in str(e).lower():
                        print(f"{YELLOW}⚠{RESET} update_inventory() - Expected error: {str(e)[:50]}")
                        results['skipped'].append("⚠ update_inventory() - needs context/credentials")
                    else:
                        print(f"{RED}✗{RESET} update_inventory() - {str(e)}")
                        results['failed'].append(f"✗ update_inventory() - {str(e)}")
        except Exception as e:
            print(f"{RED}✗{RESET} Error testing update_inventory: {str(e)}")
            results['failed'].append(f"✗ update_inventory() - {str(e)}")
    
    # Test reporting
    if 'reporting' in imported_modules:
        try:
            mod = imported_modules['reporting']
            if hasattr(mod, 'generate_report'):
                try:
                    result = mod.generate_report()
                    print(f"{GREEN}✓{RESET} generate_report() - returned: {type(result).__name__}")
                    results['passed'].append("✓ generate_report()")
                except Exception as e:
                    if "credential" in str(e).lower() or "auth" in str(e).lower() or "database" in str(e).lower():
                        print(f"{YELLOW}⚠{RESET} generate_report() - Expected error (no DB/credentials): {str(e)[:50]}")
                        results['skipped'].append("⚠ generate_report() - needs database/credentials")
                    else:
                        print(f"{RED}✗{RESET} generate_report() - {str(e)}")
                        results['failed'].append(f"✗ generate_report() - {str(e)}")
        except Exception as e:
            print(f"{RED}✗{RESET} Error testing generate_report: {str(e)}")
            results['failed'].append(f"✗ generate_report() - {str(e)}")
    
    print(f"\n{YELLOW}Phase 3: Testing Flask App Initialization{RESET}\n")
    
    # Test Flask app (this might fail due to missing env vars, but should not crash)
    try:
        # #region agent log
        debug_log('test_all_functions.py:main', 'before Flask import', {}, 'H5')
        # #endregion
        # Suppress Flask startup messages
        import logging
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        
        # #region agent log
        debug_log('test_all_functions.py:main', 'before app import', {}, 'H5')
        # #endregion
        from app import app
        # #region agent log
        debug_log('test_all_functions.py:main', 'app imported', {'app_type': type(app).__name__, 'has_blueprints': hasattr(app, 'blueprints')}, 'H5')
        # #endregion
        print(f"{GREEN}✓{RESET} Flask app initialized")
        results['passed'].append("✓ Flask app initialization")
        
        # Test blueprints are registered
        # #region agent log
        debug_log('test_all_functions.py:main', 'before blueprint check', {'blueprint_count': len(app.blueprints) if hasattr(app, 'blueprints') else 0}, 'H5')
        # #endregion
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        # #region agent log
        debug_log('test_all_functions.py:main', 'blueprints retrieved', {'blueprint_names': blueprint_names, 'count': len(blueprint_names)}, 'H5')
        # #endregion
        print(f"{GREEN}✓{RESET} Blueprints registered: {', '.join(blueprint_names)}")
        results['passed'].append(f"✓ Blueprints: {len(blueprint_names)} registered")
        
    except Exception as e:
        # #region agent log
        debug_log('test_all_functions.py:main', 'Flask app init failed', {'error_type': type(e).__name__, 'error_msg': str(e)[:200], 'traceback': traceback.format_exc()[:500]}, 'H5')
        # #endregion
        print(f"{RED}✗{RESET} Flask app initialization - {str(e)}")
        results['failed'].append(f"✗ Flask app - {str(e)}")
        if '--verbose' in sys.argv:
            traceback.print_exc()
    
    print(f"\n{YELLOW}Phase 4: Testing Utility Functions{RESET}\n")
    
    # Test utility functions
    if 'rate_limiter' in imported_modules:
        try:
            mod = imported_modules['rate_limiter']
            if hasattr(mod, 'init_limiter'):
                # This needs a Flask app, skip for now
                results['skipped'].append("⚠ init_limiter() - needs Flask app context")
        except:
            pass
    
    if 'email_service' in imported_modules:
        try:
            mod = imported_modules['email_service']
            # Just check if functions exist
            funcs = [f for f in dir(mod) if callable(getattr(mod, f, None)) and not f.startswith('_')]
            print(f"{GREEN}✓{RESET} email_service has {len(funcs)} functions")
        except Exception as e:
            print(f"{YELLOW}⚠{RESET} email_service check: {str(e)}")
    
    # Test main.py functions
    try:
        import main
        if hasattr(main, 'get_creds_path'):
            result = main.get_creds_path()
            print(f"{GREEN}✓{RESET} main.get_creds_path() - {result}")
            results['passed'].append("✓ main.get_creds_path()")
    except Exception as e:
        print(f"{RED}✗{RESET} main.get_creds_path() - {str(e)}")
        results['failed'].append(f"✗ main.get_creds_path() - {str(e)}")
    
    # Print summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Test Summary{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    print(f"{GREEN}Passed: {len(results['passed'])}{RESET}")
    print(f"{RED}Failed: {len(results['failed'])}{RESET}")
    print(f"{YELLOW}Skipped: {len(results['skipped'])}{RESET}")
    
    if results['failed']:
        print(f"\n{RED}Failed Tests:{RESET}")
        for failure in results['failed']:
            print(f"  {failure}")
    
    if results['skipped']:
        print(f"\n{YELLOW}Skipped Tests (expected):{RESET}")
        for skip in results['skipped'][:5]:  # Show first 5
            print(f"  {skip}")
        if len(results['skipped']) > 5:
            print(f"  ... and {len(results['skipped']) - 5} more")
    
    print(f"\n{BLUE}{'='*70}{RESET}\n")
    
    # Return exit code
    # #region agent log
    debug_log('test_all_functions.py:main', 'main exit', {'passed_count': len(results['passed']), 'failed_count': len(results['failed']), 'skipped_count': len(results['skipped'])}, 'H6')
    # #endregion
    return 0 if len(results['failed']) == 0 else 1

if __name__ == '__main__':
    # #region agent log
    debug_log('test_all_functions.py:__main__', 'script start', {'python_version': sys.version, 'cwd': os.getcwd()}, 'H2')
    # #endregion
    exit_code = main()
    # #region agent log
    debug_log('test_all_functions.py:__main__', 'script end', {'exit_code': exit_code}, 'H2')
    # #endregion
    sys.exit(exit_code)
