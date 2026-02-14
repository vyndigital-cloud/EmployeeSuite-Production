
import os
import sys
import mimetypes

def verify_static_assets():
    """
    PRE-FLIGHT CHECK: Verifies that static assets exist and have non-zero size.
    This script should be run before starting the Gunicorn server.
    """
    base_dir = os.path.abspath(os.path.dirname(__file__))
    static_dir = os.path.join(base_dir, 'static')
    
    print(f"🔍 [VERIFY] Checking static assets in: {static_dir}")
    
    if not os.path.exists(static_dir):
        print(f"❌ [CRITICAL] Static directory NOT FOUND at {static_dir}")
        sys.exit(1)
        
    found_files = 0
    empty_files = 0
    
    for root, dirs, files in os.walk(static_dir):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, base_dir)
            size = os.path.getsize(file_path)
            found_files += 1
            
            status = "✅ OK"
            if size == 0:
                status = "❌ EMPTY (0 bytes)"
                empty_files += 1
            
            # Check MIME estimation
            mime_type, _ = mimetypes.guess_type(file_path)
            
            print(f"{status} | {size} bytes | {mime_type} | {rel_path}")

            # [READ CHECK] Try to read the file content to prove accessibility
            if size > 0 and file.endswith('.js'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        head = f.read(100)
                        print(f"   📖 Content Check (First 100 chars): {head[:50]}...")
                except Exception as e:
                    print(f"   ❌ READ ERROR: {e}")
                    sys.exit(1)
            
    print("-" * 50)
    print(f"📊 Report: Found {found_files} files. {empty_files} are 0 bytes.")
    
    if empty_files > 0:
        print("❌ [FAILURE] Deployment contains empty static files.")
        sys.exit(1)
    
    print("✅ [SUCCESS] Static assets verified.")

if __name__ == "__main__":
    verify_static_assets()
