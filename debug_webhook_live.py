
import requests

TARGET_URL = "https://employeesuite-production.onrender.com"
WEBHOOK_URL = f"{TARGET_URL}/webhooks/app/uninstall"

print(f"Checking {WEBHOOK_URL}...")
try:
    # 1. Try GET (Expect 405 Method Not Allowed)
    r_get = requests.get(WEBHOOK_URL, timeout=5)
    print(f"GET Status: {r_get.status_code}")
    print(f"GET Content: {r_get.text[:100]}")

    # 2. Try POST with no signature (Expect 401 Unauthorized)
    r_post = requests.post(WEBHOOK_URL, timeout=5)
    print(f"POST Status: {r_post.status_code}")
    print(f"POST Content: {r_post.text[:100]}")

except Exception as e:
    print(f"Error: {e}")
