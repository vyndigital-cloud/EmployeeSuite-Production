
import os
import re

def scan_for_deprecated_usage(root_dir):
    deprecated_pattern = re.compile(r'verify_session_token')
    stateless_auth_pattern = re.compile(r'stateless_auth')
    
    issues = []
    
    # Files to ignore
    ignore_files = ['session_token_verification.py', 'verify_auth_refactor.py', 'task.md', 'implementation_plan.md']
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if 'venv' in dirpath or '.git' in dirpath or '__pycache__' in dirpath:
            continue
            
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
                
            if filename in ignore_files:
                continue
                
            filepath = os.path.join(dirpath, filename)
            
            with open(filepath, 'r') as f:
                content = f.read()
                
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if deprecated_pattern.search(line):
                    # Check if it's a comment
                    if line.strip().startswith('#'):
                        continue
                    # Check if it's a string literal (rough check)
                    if '"verify_session_token"' in line or "'verify_session_token'" in line:
                        continue
                        
                    issues.append(f"DEPRECATED USAGE: {filename}:{i+1}: {line.strip()}")
    
    return issues

if __name__ == "__main__":
    root_dir = os.getcwd()
    print(f"Scanning {root_dir} for deprecated verify_session_token usage...")
    
    issues = scan_for_deprecated_usage(root_dir)
    
    if issues:
        print("\n❌ Found issues:")
        for issue in issues:
            print(issue)
        exit(1)
    else:
        print("\n✅ No deprecated usage found!")
        exit(0)
