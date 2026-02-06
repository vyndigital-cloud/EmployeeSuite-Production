#!/usr/bin/env python3
"""
Comprehensive test of Shopify app URLs and routing
"""
import requests
import json
from urllib.parse import urlparse, urljoin

# Base URL
BASE_URL = "https://employeesuite-production.onrender.com"

# Test endpoints
ENDPOINTS = [
    "/",
    "/dashboard",
    "/install",
    "/auth/callback",
    "/features/dashboard",
    "/api/dashboard/comprehensive",
]

def test_endpoint(url):
    """Test a single endpoint"""
    print(f"\n{'='*80}")
    print(f"Testing: {url}")
    print(f"{'='*80}")
    
    try:
        # Test with HEAD request first (faster)
        response = requests.head(url, allow_redirects=True, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Final URL: {response.url}")
        
        # Check for redirects
        if response.history:
            print(f"\nRedirect Chain:")
            for i, resp in enumerate(response.history, 1):
                print(f"  {i}. {resp.status_code} -> {resp.url}")
            print(f"  Final: {response.status_code} -> {response.url}")
        
        # Important headers
        print(f"\nKey Headers:")
        headers_to_check = [
            'content-type',
            'location',
            'content-security-policy',
            'x-frame-options',
            'strict-transport-security'
        ]
        
        for header in headers_to_check:
            if header in response.headers:
                value = response.headers[header]
                if len(value) > 100:
                    value = value[:100] + "..."
                print(f"  {header}: {value}")
        
        # Status interpretation
        if response.status_code == 200:
            print(f"\n✅ SUCCESS: Endpoint is accessible")
        elif response.status_code == 302 or response.status_code == 301:
            print(f"\n🔄 REDIRECT: Endpoint redirects to {response.headers.get('location', 'unknown')}")
        elif response.status_code == 404:
            print(f"\n❌ NOT FOUND: Endpoint does not exist")
        elif response.status_code == 401:
            print(f"\n🔒 UNAUTHORIZED: Authentication required")
        elif response.status_code == 403:
            print(f"\n🚫 FORBIDDEN: Access denied")
        else:
            print(f"\n⚠️  UNEXPECTED: Status code {response.status_code}")
            
        return response.status_code
        
    except requests.exceptions.Timeout:
        print(f"\n⏱️  TIMEOUT: Request took too long")
        return None
    except requests.exceptions.ConnectionError:
        print(f"\n🔌 CONNECTION ERROR: Could not connect to server")
        return None
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return None

def test_shopify_oauth_flow():
    """Test the Shopify OAuth flow"""
    print(f"\n{'='*80}")
    print(f"Testing Shopify OAuth Flow")
    print(f"{'='*80}")
    
    # Test install endpoint with shop parameter
    test_shop = "test-store.myshopify.com"
    install_url = f"{BASE_URL}/install?shop={test_shop}"
    
    print(f"\n1. Testing install endpoint: {install_url}")
    try:
        response = requests.get(install_url, allow_redirects=False, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code in [302, 301]:
            redirect_location = response.headers.get('location', '')
            print(f"   Redirects to: {redirect_location}")
            
            # Check if it's redirecting to Shopify OAuth
            if 'myshopify.com' in redirect_location and 'oauth/authorize' in redirect_location:
                print(f"   ✅ Correctly redirects to Shopify OAuth")
            else:
                print(f"   ⚠️  Unexpected redirect location")
        else:
            print(f"   ⚠️  Expected redirect (302), got {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

def check_shopify_app_config():
    """Check shopify.app.toml configuration"""
    print(f"\n{'='*80}")
    print(f"Checking Shopify App Configuration")
    print(f"{'='*80}")
    
    try:
        with open('shopify.app.toml', 'r') as f:
            content = f.read()
            
        print("\nKey Configuration Values:")
        
        # Extract key values
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('application_url'):
                print(f"  {line}")
                # Check for trailing slash
                if line.endswith('/"') or line.endswith("/'"):
                    print(f"    ⚠️  WARNING: Trailing slash detected!")
                else:
                    print(f"    ✅ No trailing slash")
            elif line.startswith('client_id'):
                print(f"  {line}")
            elif line.startswith('handle'):
                print(f"  {line}")
            elif line.startswith('embedded'):
                print(f"  {line}")
            elif 'redirect_urls' in line:
                print(f"  {line}")
                
    except FileNotFoundError:
        print("  ❌ shopify.app.toml not found")
    except Exception as e:
        print(f"  ❌ Error reading config: {str(e)}")

def test_dashboard_with_params():
    """Test dashboard with various query parameters"""
    print(f"\n{'='*80}")
    print(f"Testing Dashboard with Query Parameters")
    print(f"{'='*80}")
    
    test_cases = [
        "/dashboard",
        "/dashboard?shop=test-store.myshopify.com",
        "/dashboard?shop=test-store.myshopify.com&host=dGVzdC1zdG9yZS5teXNob3BpZnkuY29tL2FkbWlu",
    ]
    
    for endpoint in test_cases:
        url = f"{BASE_URL}{endpoint}"
        print(f"\nTesting: {endpoint}")
        try:
            response = requests.head(url, allow_redirects=True, timeout=10)
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print(f"  ✅ Success")
            elif response.status_code in [301, 302]:
                print(f"  🔄 Redirects to: {response.url}")
            else:
                print(f"  ⚠️  Status: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")

def main():
    """Run all tests"""
    print(f"\n{'#'*80}")
    print(f"# SHOPIFY APP URL TESTING SUITE")
    print(f"# Base URL: {BASE_URL}")
    print(f"{'#'*80}")
    
    # Test 1: Check configuration
    check_shopify_app_config()
    
    # Test 2: Test all endpoints
    print(f"\n\n{'#'*80}")
    print(f"# ENDPOINT TESTS")
    print(f"{'#'*80}")
    
    results = {}
    for endpoint in ENDPOINTS:
        url = urljoin(BASE_URL, endpoint)
        status = test_endpoint(url)
        results[endpoint] = status
    
    # Test 3: OAuth flow
    print(f"\n\n{'#'*80}")
    print(f"# OAUTH FLOW TEST")
    print(f"{'#'*80}")
    test_shopify_oauth_flow()
    
    # Test 4: Dashboard with parameters
    test_dashboard_with_params()
    
    # Summary
    print(f"\n\n{'#'*80}")
    print(f"# TEST SUMMARY")
    print(f"{'#'*80}")
    
    print(f"\nEndpoint Status Summary:")
    for endpoint, status in results.items():
        if status == 200:
            icon = "✅"
        elif status in [301, 302]:
            icon = "🔄"
        elif status == 404:
            icon = "❌"
        elif status in [401, 403]:
            icon = "🔒"
        else:
            icon = "⚠️ "
        
        print(f"  {icon} {endpoint}: {status}")
    
    print(f"\n{'#'*80}")
    print(f"# RECOMMENDATIONS")
    print(f"{'#'*80}")
    
    print("""
1. Check Shopify Partners Dashboard:
   - Go to: https://partners.shopify.com
   - Navigate to: Apps → Employee Suite → Configuration
   - Verify "App URL" has NO trailing slash
   - Should be: https://employeesuite-production.onrender.com
   - NOT: https://employeesuite-production.onrender.com/

2. Check "Allowed redirection URLs":
   - Should include: https://employeesuite-production.onrender.com/auth/callback
   - Exact match, no query parameters

3. If you see double slash (//dashboard):
   - This confirms trailing slash in Partners Dashboard
   - Remove it and save
   - Clear browser cache
   - Try again

4. Test the app:
   - Install in a development store
   - Check that it loads embedded in Shopify admin
   - Verify no 404 errors
""")

if __name__ == "__main__":
    main()
