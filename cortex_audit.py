import os
import ast
import sys
import importlib.util
import re
from flask import Flask

# Configuration
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {'.git', '__pycache__', 'venv', 'env', 'migrations'}
SKIP_FILES = {'cortex_audit.py', 'debug_access.py', 'wsgi.py'}

def get_python_files(root_dir):
    py_files = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            if file.endswith('.py') and file not in SKIP_FILES:
                py_files.append(os.path.join(root, file))
    return py_files

def check_syntax(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        compile(source, file_path, 'exec')
        return True, None
    except Exception as e:
        return False, str(e)

def extract_template_calls(file_path):
    templates = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'render_template':
                    if node.args and isinstance(node.args[0], ast.Constant): # Python 3.8+
                        templates.append(node.args[0].value)
                    elif node.args and isinstance(node.args[0], ast.Str): # Python 3.7
                        templates.append(node.args[0].s)
    except Exception:
        pass # checking syntax separately
    return templates

def check_imports(file_path):
    module_name = os.path.basename(file_path).replace('.py', '')
    if module_name == 'main': return True, None # Skip main execution
    
    # Simple check: can we verify imports?
    # Actually, attempting to import everything might trigger side effects (init db, etc)
    # Safer to check if dependencies exist. 
    # For now, we will trust the app factory check for deep integration.
    return True, None

def run_audit():
    print(f"🚀 Starting Cortex System Audit on {PROJECT_ROOT}\n")
    
    python_files = get_python_files(PROJECT_ROOT)
    print(f"Found {len(python_files)} Python files to scan.\n")
    
    errors = []
    warnings = []
    template_refs = set()
    
    # 1. Syntax Check
    print("MATCHING FILES...")
    for file_path in python_files:
        rel_path = os.path.relpath(file_path, PROJECT_ROOT)
        is_valid, error = check_syntax(file_path)
        if is_valid:
            print(f"  ✅ {rel_path}: Syntax OK")
            # Extract templates while we are here
            refs = extract_template_calls(file_path)
            for t in refs:
                template_refs.add((t, rel_path))
        else:
            print(f"  ❌ {rel_path}: SYNTAX ERROR - {error}")
            errors.append(f"{rel_path}: Syntax Error: {error}")

    print("\n" + "="*50 + "\n")

    # 2. App Factory Integration Test
    print("TESTING APP INITIALIZATION...")
    try:
        sys.path.append(PROJECT_ROOT)
        from app_factory import create_app
        app = create_app()
        print("  ✅ App Factory initialized successfully")
        print(f"  ✅ Registered Blueprints: {list(app.blueprints.keys())}")
        
        if hasattr(app, 'config') and 'FAILED_BLUEPRINTS' in app.config:
             print(f"  ❌ Failed Blueprints detected: {app.config['FAILED_BLUEPRINTS']}")
             errors.append(f"Blueprint Registration Failed: {app.config['FAILED_BLUEPRINTS']}")
        
    except Exception as e:
        print(f"  ❌ App Factory CRASHED: {e}")
        errors.append(f"App Factory Crash: {e}")

    print("\n" + "="*50 + "\n")

    # 3. Template Verification
    print("VERIFYING TEMPLATES...")
    template_dir = os.path.join(PROJECT_ROOT, 'templates')
    
    for template_name, source_file in template_refs:
        # Handle subfolders in template name
        full_path = os.path.join(template_dir, template_name)
        if os.path.exists(full_path):
            print(f"  ✅ {template_name} (found)")
        else:
            # Try to handle some dynamic cases or partial matches?
            # For now, strict check
            print(f"  ❌ {template_name} NOT FOUND (referenced in {source_file})")
            errors.append(f"Missing Template: {template_name} (referenced in {source_file})")

    print("\n" + "="*50 + "\n")
    
    if errors:
        print(f"🚨 AUDIT FAILED with {len(errors)} errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("✅ SYSTEM AUDIT PASSED: All checks passed.")
        sys.exit(0)

if __name__ == '__main__':
    run_audit()
