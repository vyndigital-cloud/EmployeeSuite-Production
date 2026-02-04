import os
import jwt
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

APP_URL = os.getenv("APP_URL", "http://localhost:5000")
API_SECRET = os.getenv("SHOPIFY_API_SECRET")
API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOP = "demo-store.myshopify.com"  # Using a known test shop

def generate_test_token():
    """Generates a valid JWT token signed with our secret"""
    payload = {
        "iss": f"https://{SHOP}/admin",
        "dest": f"https://{SHOP}",
        "aud": API_KEY,
        "sub": "1234567890",
        "exp": int(time.time()) + 3600,
        "nbf": int(time.time()),
        "iat": int(time.time()),
        "sid": "1234567890"
    }
    encoded_jwt = jwt.encode(payload, API_SECRET, algorithm="HS256")
    return encoded_jwt

def test_embedded_auth():
    print(f"Testing Auth Fix against {APP_URL}...")
    
    # 1. Generate Token
    token = generate_test_token()
    print(f"Generated Test Token: {token[:15]}...")

    # 2. Simulate Request with Token (Authorization Header)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # We hit a protected endpoint (e.g., /api/process_orders which requires login)
    url = f"{APP_URL}/api/process_orders"
    print(f"Requesting Protected URL: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Request accepted with Token! No redirect loop.")
            # Verify it's actually data and not a login page
            if "success" in response.json():
                print("✅ Data returned successfully.")
            else:
                print("⚠️ Warning: 200 OK but unexpected JSON response.")
        elif response.status_code == 302:
            print("❌ FAILURE: Redirected to login page. The fix is NOT working.")
            print(f"Redirect Location: {response.headers.get('Location')}")
        else:
            print(f"❌ FAILURE: Unexpected status code {response.status_code}")
            print(response.text[:200])

    except Exception as e:
        print(f"❌ ERROR: Request failed - {e}")

if __name__ == "__main__":
    if not API_SECRET or not API_KEY:
        print("❌ Error: Missing SHOPIFY_API_KEY or SHOPIFY_API_SECRET env vars")
    else:
        test_embedded_auth()
