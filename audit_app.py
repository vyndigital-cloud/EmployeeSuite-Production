#!/usr/bin/env python3
"""
Comprehensive Application Audit Script
Validates code quality, security, and production readiness
"""

import re
import os
from pathlib import Path
from collections import defaultdict

class AuditReport:
    def __init__(self):
        self.issues = defaultdict(list)
        self.warnings = defaultdict(list)
        self.info = defaultdict(list)
        
    def add_issue(self, category, message):
        self.issues[category].append(message)
    
    def add_warning(self, category, message):
        self.warnings[category].append(message)
        
    def add_info(self, category, message):
        self.info[category].append(message)
    
    def print_report(self):
        print("=" * 80)
        print("COMPREHENSIVE APPLICATION AUDIT REPORT")
        print("=" * 80)
        
        if self.issues:
            print("\n🔴 CRITICAL ISSUES (Must Fix):")
            for category, items in self.issues.items():
                print(f"\n  [{category}]")
                for item in items:
                    print(f"    ❌ {item}")
        
        if self.warnings:
            print("\n🟡 WARNINGS (Should Review):")
            for category, items in self.warnings.items():
                print(f"\n  [{category}]")
                for item in items:
                    print(f"    ⚠️  {item}")
        
        if self.info:
            print("\n🔵 INFO (Good to Know):")
            for category, items in self.info.items():
                print(f"\n  [{category}]")
                for item in items:
                    print(f"    ℹ️  {item}")
        
        print("\n" + "=" * 80)
        total_issues = sum(len(items) for items in self.issues.values())
        total_warnings = sum(len(items) for items in self.warnings.values())
        print(f"Summary: {total_issues} critical issues, {total_warnings} warnings")
        print("=" * 80)

def check_jinja_balance(file_path, report):
    """Check if Jinja if/endif tags are balanced"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if_count = len(re.findall(r'{%\s*if\s', content))
        endif_count = len(re.findall(r'{%\s*endif\s*%}', content))
        
        if if_count != endif_count:
            report.add_issue("Template Syntax", 
                f"{file_path.name}: Unbalanced if/endif ({if_count} if vs {endif_count} endif)")
        else:
            report.add_info("Template Syntax", 
                f"{file_path.name}: ✅ Balanced ({if_count} pairs)")
    except Exception as e:
        report.add_warning("File Read", f"Could not read {file_path.name}: {e}")

def check_duplicate_imports(file_path, report):
    """Check for duplicate import statements"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        imports = {}
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*(from\s+[\w.]+\s+)?import\s+([\w,\s]+)', line)
            if match:
                import_stmt = line.strip()
                if import_stmt in imports:
                    report.add_issue("Duplicate Imports",
                        f"{file_path.name}:{i} - Duplicate: {import_stmt} (first at line {imports[import_stmt]})")
                else:
                    imports[import_stmt] = i
    except Exception as e:
        report.add_warning("File Read", f"Could not read {file_path.name}: {e}")

def check_hardcoded_secrets(file_path, report):
    """Check for potential hardcoded secrets"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Patterns that might indicate hardcoded secrets
        patterns = [
            (r'password\s*=\s*["\'][^"\']{8,}["\']', 'password'),
            (r'api[_-]?key\s*=\s*["\'][^"\']{20,}["\']', 'API key'),
            (r'secret\s*=\s*["\'][^"\']{20,}["\']', 'secret'),
            (r'token\s*=\s*["\'][^"\']{20,}["\']', 'token'),
        ]
        
        for i, line in enumerate(lines, 1):
            # Skip comments and env var assignments
            if line.strip().startswith('#') or 'os.getenv' in line or 'os.environ' in line:
                continue
                
            for pattern, secret_type in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Exclude common dev/test values
                    if 'dev-secret' not in line.lower() and 'test' not in line.lower():
                        report.add_warning("Security",
                            f"{file_path.name}:{i} - Possible hardcoded {secret_type}")
    except Exception as e:
        report.add_warning("File Read", f"Could not read {file_path.name}: {e}")

def check_error_handling(file_path, report):
    """Check for bare except clauses"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            if re.match(r'^\s*except\s*:', line):
                report.add_warning("Error Handling",
                    f"{file_path.name}:{i} - Bare except clause (should specify exception type)")
    except Exception as e:
        report.add_warning("File Read", f"Could not read {file_path.name}: {e}")

def main():
    report = AuditReport()
    project_root = Path('/Users/essentials/MissionControl')
    
    # Check Python files
    python_files = list(project_root.glob('*.py'))
    
    print(f"Auditing {len(python_files)} Python files...\n")
    
    for py_file in python_files:
        # Skip test files and migrations
        if 'test_' in py_file.name or 'migrate_' in py_file.name:
            continue
            
        check_jinja_balance(py_file, report)
        check_duplicate_imports(py_file, report)
        check_hardcoded_secrets(py_file, report)
        check_error_handling(py_file, report)
    
    report.print_report()
    
    # Return exit code based on critical issues
    return 1 if report.issues else 0

if __name__ == '__main__':
    exit(main())
