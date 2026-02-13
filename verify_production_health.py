
import requests
import time
import socket
import ssl
from urllib.parse import urlparse

TARGET_URL = "https://employeesuite-production.onrender.com"

print(f"🏥 STARTING FULL SYSTEM DIAGNOSTICS FOR: {TARGET_URL}\n")

issues = []

def check(name, func):
    print(f"Checking {name}...", end=" ", flush=True)
    try:
        start = time.time()
        result = func()
        duration = (time.time() - start) * 1000
        if result:
            print(f"✅ OK ({duration:.0f}ms)")
            return True
        else:
            print(f"❌ FAILED ({duration:.0f}ms)")
            issues.append(name)
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        issues.append(f"{name} ({e})")
        return False

# 1. SSL/TLS Verification
def check_ssl():
    hostname = urlparse(TARGET_URL).hostname
    context = ssl.create_default_context()
    with socket.create_connection((hostname, 443)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            return ssock.version() == 'TLSv1.3' or ssock.version() == 'TLSv1.2'

check("SSL/TLS Security", check_ssl)

# 2. Latency / Root Response
def check_root():
    r = requests.get(TARGET_URL, timeout=5)
    # 200 or 302 (redirect to login) is fine
    return r.status_code in [200, 302]

check("Core Server Response", check_root)

# 3. Static Assets (CSS/JS)
def check_assets():
    # Check a likely existing asset
    r = requests.get(f"{TARGET_URL}/static/js/dashboard.js", timeout=5)
    return r.status_code == 200

check("CDN/Static Asset Delivery", check_assets)

# 4. App Bridge Script (Context)
# Not a file checks, but route check
def check_legal():
    r = requests.get(f"{TARGET_URL}/privacy", timeout=5)
    return "Privacy Policy" in r.text

check("Public Routes & Rendering", check_legal)

# 5. API/Webhook Health (Method Not Allowed is GOOD - means endpoint exists)
def check_api():
    r = requests.get(f"{TARGET_URL}/webhooks/app/uninstall", timeout=5)
    # 405 Method Not Allowed means Flask found the route but expects POST
    # 404 would mean route missing
    return r.status_code == 405

check("API/Webhook Endpoints", check_api)

print("\n------------------------------")
if not issues:
    print("🚀 ALL SYSTEMS OPERATIONAL. Production environment is healthy.")
else:
    print(f"⚠️  ISSUES DETECTED: {', '.join(issues)}")
