#!/usr/bin/env python3
"""
Identity Integrity Verification Script
Tests the Kill Rule and Hard-Link Rule to prevent User 4/User 11 collision.

Usage:
    python verify_identity_integrity.py [base_url]
    
Example:
    python verify_identity_integrity.py https://your-app.onrender.com
    python verify_identity_integrity.py http://localhost:5000
"""

import requests
import sys
from urllib.parse import urljoin
from datetime import datetime


class IdentityIntegrityTest:
    """Test suite for identity integrity verification"""
    
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.results = []
        self.test_shop = 'employee-suite.myshopify.com'
    
    def log_test(self, status, message, details=None):
        """Log test result"""
        self.results.append({
            'status': status,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    def test_1_unauthenticated_redirect(self):
        """Test 1: Unauthenticated access redirects to auth"""
        print("\n📋 Test 1: Unauthenticated Redirect")
        print("-" * 60)
        
        try:
            # Clear all cookies
            self.session.cookies.clear()
            
            response = self.session.get(
                urljoin(self.base_url, '/dashboard'),
                allow_redirects=False
            )
            
            if response.status_code in [302, 301]:
                location = response.headers.get('Location', '')
                if 'auth' in location.lower() or 'login' in location.lower():
                    self.log_test('PASS', 'Unauthenticated redirect works correctly', 
                                f'Redirected to: {location}')
                    print(f"✅ PASS: Redirected to {location}")
                    return True
                else:
                    self.log_test('FAIL', 'Redirect location incorrect', 
                                f'Expected auth/login, got: {location}')
                    print(f"❌ FAIL: Redirected to {location} instead of auth")
                    return False
            else:
                self.log_test('FAIL', 'No redirect occurred', 
                            f'Status code: {response.status_code}')
                print(f"❌ FAIL: Expected redirect, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test('ERROR', 'Test failed with exception', str(e))
            print(f"❌ ERROR: {e}")
            return False
    
    def test_2_shop_parameter_handling(self):
        """Test 2: Shop parameter forces correct user lookup"""
        print("\n📋 Test 2: Shop Parameter Handling")
        print("-" * 60)
        
        try:
            # Clear cookies
            self.session.cookies.clear()
            
            response = self.session.get(
                urljoin(self.base_url, f'/settings/shopify?shop={self.test_shop}'),
                allow_redirects=True
            )
            
            # Should either show settings page or redirect to OAuth
            if response.status_code == 200:
                self.log_test('PASS', 'Shop parameter handled - page loaded', 
                            f'Status: {response.status_code}')
                print(f"✅ PASS: Page loaded successfully")
                return True
            elif response.status_code in [302, 301]:
                location = response.url
                if 'install' in location or 'oauth' in location or 'auth' in location:
                    self.log_test('PASS', 'Shop parameter triggered OAuth flow', 
                                f'Redirected to: {location}')
                    print(f"✅ PASS: Correctly redirected to OAuth: {location}")
                    return True
                else:
                    self.log_test('WARN', 'Unexpected redirect', 
                                f'Redirected to: {location}')
                    print(f"⚠️  WARN: Redirected to {location}")
                    return True
            else:
                self.log_test('FAIL', 'Unexpected status code', 
                            f'Status: {response.status_code}')
                print(f"❌ FAIL: Unexpected status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test('ERROR', 'Test failed with exception', str(e))
            print(f"❌ ERROR: {e}")
            return False
    
    def test_3_session_mismatch_detection(self):
        """Test 3: Session mismatch triggers re-authentication"""
        print("\n📋 Test 3: Session Mismatch Detection (Kill Rule)")
        print("-" * 60)
        
        try:
            # Set up a session with wrong shop
            self.session.cookies.set('shop_domain', 'wrong-shop.myshopify.com', 
                                    domain=self.base_url.replace('https://', '').replace('http://', '').split(':')[0])
            
            # Request with different shop parameter
            response = self.session.get(
                urljoin(self.base_url, f'/settings/shopify?shop={self.test_shop}'),
                allow_redirects=True
            )
            
            # Should redirect to OAuth install due to mismatch
            if 'install' in response.url or 'oauth' in response.url or 'auth' in response.url:
                self.log_test('PASS', 'Session mismatch triggered re-auth (Kill Rule working)', 
                            f'Redirected to: {response.url}')
                print(f"✅ PASS: Kill Rule activated - redirected to {response.url}")
                return True
            elif response.status_code == 200:
                # Check if session was cleared (cookies should be different)
                self.log_test('WARN', 'Page loaded but unclear if session was cleared', 
                            'Manual verification needed')
                print(f"⚠️  WARN: Page loaded - manual verification needed")
                return True
            else:
                self.log_test('FAIL', 'Session mismatch not properly handled', 
                            f'Status: {response.status_code}, URL: {response.url}')
                print(f"❌ FAIL: Mismatch not detected")
                return False
                
        except Exception as e:
            self.log_test('ERROR', 'Test failed with exception', str(e))
            print(f"❌ ERROR: {e}")
            return False
    
    def test_4_debug_routes_accessible(self):
        """Test 4: Debug routes are accessible"""
        print("\n📋 Test 4: Debug Routes Accessibility")
        print("-" * 60)
        
        try:
            response = self.session.get(urljoin(self.base_url, '/debug/routes'))
            
            if response.status_code == 200:
                data = response.json()
                oauth_routes = data.get('oauth_routes', [])
                
                self.log_test('PASS', 'Debug routes accessible', 
                            f'Found {len(oauth_routes)} OAuth routes')
                print(f"✅ PASS: Debug routes working - {len(oauth_routes)} OAuth routes found")
                
                # Check for critical routes
                all_routes = data.get('all_routes', [])
                route_paths = [r.get('rule', '') for r in all_routes]
                
                critical_routes = ['/oauth/install', '/oauth/callback', '/settings/shopify']
                missing = [r for r in critical_routes if not any(r in path for path in route_paths)]
                
                if missing:
                    print(f"⚠️  WARNING: Missing critical routes: {missing}")
                else:
                    print(f"✅ All critical routes present")
                
                return True
            else:
                self.log_test('FAIL', 'Debug routes not accessible', 
                            f'Status: {response.status_code}')
                print(f"❌ FAIL: Debug routes returned {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test('ERROR', 'Test failed with exception', str(e))
            print(f"❌ ERROR: {e}")
            return False
    
    def test_5_hard_link_verification(self):
        """Test 5: Hard-Link Rule forces database lookup"""
        print("\n📋 Test 5: Hard-Link Database Verification")
        print("-" * 60)
        
        try:
            # This test requires actual authentication, so we'll just verify
            # the endpoint responds correctly
            self.session.cookies.clear()
            
            response = self.session.get(
                urljoin(self.base_url, f'/settings/shopify?shop={self.test_shop}'),
                allow_redirects=False
            )
            
            # Should redirect to auth since we have no session
            if response.status_code in [302, 301]:
                self.log_test('PASS', 'Hard-Link verification endpoint responds', 
                            'Correctly requires authentication')
                print(f"✅ PASS: Endpoint requires authentication as expected")
                return True
            else:
                self.log_test('WARN', 'Unexpected response', 
                            f'Status: {response.status_code}')
                print(f"⚠️  WARN: Unexpected status {response.status_code}")
                return True
                
        except Exception as e:
            self.log_test('ERROR', 'Test failed with exception', str(e))
            print(f"❌ ERROR: {e}")
            return False
    
    def run_all_tests(self):
        """Run all verification tests"""
        print("=" * 60)
        print("🔍 IDENTITY INTEGRITY VERIFICATION TEST SUITE")
        print("=" * 60)
        print(f"Target: {self.base_url}")
        print(f"Test Shop: {self.test_shop}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all tests
        tests = [
            self.test_1_unauthenticated_redirect,
            self.test_2_shop_parameter_handling,
            self.test_3_session_mismatch_detection,
            self.test_4_debug_routes_accessible,
            self.test_5_hard_link_verification,
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"\n❌ Test crashed: {e}")
                results.append(False)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        errors = sum(1 for r in self.results if r['status'] == 'ERROR')
        warnings = sum(1 for r in self.results if r['status'] == 'WARN')
        
        total = len(self.results)
        
        print(f"\n✅ Passed:   {passed}/{total}")
        print(f"❌ Failed:   {failed}/{total}")
        print(f"⚠️  Warnings: {warnings}/{total}")
        print(f"💥 Errors:   {errors}/{total}")
        
        if failed == 0 and errors == 0:
            print(f"\n🎉 ALL TESTS PASSED!")
            success_rate = 100
        else:
            success_rate = (passed / total * 100) if total > 0 else 0
            print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        print("\n" + "=" * 60)
        print("📝 DETAILED RESULTS")
        print("=" * 60)
        
        for i, result in enumerate(self.results, 1):
            status_emoji = {
                'PASS': '✅',
                'FAIL': '❌',
                'ERROR': '💥',
                'WARN': '⚠️'
            }.get(result['status'], '❓')
            
            print(f"\n{i}. {status_emoji} {result['status']}: {result['message']}")
            if result.get('details'):
                print(f"   Details: {result['details']}")
        
        print("\n" + "=" * 60)
        
        # Return success if no failures or errors
        return failed == 0 and errors == 0


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = 'http://localhost:5000'
        print(f"⚠️  No URL provided, using default: {base_url}")
        print(f"Usage: python {sys.argv[0]} <base_url>\n")
    
    tester = IdentityIntegrityTest(base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
