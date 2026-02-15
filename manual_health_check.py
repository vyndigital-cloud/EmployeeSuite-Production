import requests
import sys
import time

def check_health(url):
    print(f"🔍 Checking {url}...")
    try:
        start = time.time()
        response = requests.get(url, timeout=5)
        latency = (time.time() - start) * 1000
        
        if response.status_code == 200:
            print(f"✅ SUCCESS: {url} returned 200 OK")
            print(f"⚡ Latency: {latency:.2f}ms")
            print(f"📄 Content: {response.text[:50]}...")
            return True
        else:
            print(f"❌ FAILURE: {url} returned {response.status_code}")
            print(f"📉 Latency: {latency:.2f}ms")
            print(f"📄 Content: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"💥 CRASH: Connection failed - {e}")
        return False

if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "https://employee-suite-production.onrender.com"
    
    print("="*40)
    print("SOVEREIGN SYSTEM: MANUAL HEALTH CHECK")
    print("="*40)
    
    # 1. Check Root
    check_health(f"{base_url}/")
    
    # 2. Check Health
    check_health(f"{base_url}/health")
    
    # 3. Check Head (Simulated)
    try:
        print(f"🔍 Checking HEAD {base_url}/...")
        start = time.time()
        response = requests.head(f"{base_url}/", timeout=5)
        latency = (time.time() - start) * 1000
        print(f"ℹ️  HEAD Status: {response.status_code}")
        print(f"⚡ Latency: {latency:.2f}ms")
    except Exception as e:
        print(f"💥 HEAD Request Failed: {e}")

    print("="*40)
