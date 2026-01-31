import urllib.request
import urllib.error
import json

# Configuration
APP_URL = "http://localhost:5000"  # Adjust if running on a different port
API_ENDPOINT = f"{APP_URL}/api/generate_report"

def test_generate_report():
    print(f"Testing {API_ENDPOINT}...")
    
    # scenario 1: No auth
    req = urllib.request.Request(API_ENDPOINT, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            print(f"No Auth Response: {response.getcode()}")
            print(response.read().decode('utf-8')[:200])
    except urllib.error.HTTPError as e:
        print(f"No Auth Failed: {e.code}")
        print(e.read().decode('utf-8')[:200])
    except Exception as e:
        print(f"No Auth Request failed: {e}")

    # scenario 2: Invalid Auth
    req = urllib.request.Request(API_ENDPOINT, method='POST')
    req.add_header("Authorization", "Bearer invalid_token")
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Invalid Auth Response: {response.getcode()}")
            print(response.read().decode('utf-8')[:200])
    except urllib.error.HTTPError as e:
        print(f"Invalid Auth Failed: {e.code}")
        print(e.read().decode('utf-8')[:200])
    except Exception as e:
        print(f"Invalid Auth Request failed: {e}")

if __name__ == "__main__":
    test_generate_report()
