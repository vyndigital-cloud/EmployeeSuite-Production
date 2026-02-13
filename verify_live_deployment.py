
import requests
import sys

BASE_URL = "https://employeesuite-production.onrender.com"

def check_endpoint(path, method="GET", expected_codes=[200]):
    url = f"{BASE_URL}{path}"
    try:
        if method == "POST":
            response = requests.post(url, timeout=10)
        else:
            response = requests.get(url, timeout=10)
        
        print(f"[{method}] {path}: {response.status_code}")
        
        if response.status_code in expected_codes:
            print(f"✅ PASS: {path} returned {response.status_code}")
            return True
        else:
            print(f"❌ FAIL: {path} returned {response.status_code} (Expected {expected_codes})")
            return False
    except Exception as e:
        print(f"❌ ERROR: {path} - {e}")
        return False

print(f"Verifying Live Deployment at {BASE_URL}...\n")

# 1. Critical GDPR Check (The fix I made)
# POST to /webhooks/customers/data_request
# If blueprint is registered: 400 (Missing headers) or 401 (Invalid signature)
# If blueprint is MISSING: 404 (Not Found)
print("--- GDPR Webhook Verification ---")
# Using 400, 401, 405 as non-404 indicators of existence
gdpr_ok = check_endpoint("/webhooks/customers/data_request", "POST", [400, 401]) 
check_endpoint("/webhooks/customers/redact", "POST", [400, 401])
check_endpoint("/webhooks/shop/redact", "POST", [400, 401])

# 2. Public Pages
print("\n--- Public Page Verification ---")
pages_ok = True
pages_ok &= check_endpoint("/privacy", "GET", [200]) # Corrected from /legal/privacy
pages_ok &= check_endpoint("/terms", "GET", [200])   # Corrected from /legal/terms
pages_ok &= check_endpoint("/faq", "GET", [200])
pages_ok &= check_endpoint("/support", "GET", [200])

# 3. Auth/Admin
print("\n--- Auth/Admin Verification ---")
# /login should load (200)
check_endpoint("/login", "GET", [200])
# /system-admin/login should load (200) - prefix is /system-admin
check_endpoint("/system-admin/login", "GET", [200])

if gdpr_ok and pages_ok:
    print("\n✅ LIVE DEPLOYMENT VERIFIED")
    sys.exit(0)
else:
    print("\n❌ VERIFICATION FAILED")
    sys.exit(1)
