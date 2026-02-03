"""
Comprehensive Stress Test Suite for Employee Suite
Tests all major functionality under load
"""

import asyncio
import concurrent.futures
import json
import random
import time
from datetime import datetime, timedelta
from threading import Thread
import requests
import pytest
from urllib.parse import urlencode

class EmployeeSuiteStressTest:
    def __init__(self, base_url="http://localhost:5000", max_workers=50):
        self.base_url = base_url.rstrip('/')
        self.max_workers = max_workers
        self.results = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'errors': [],
            'endpoint_stats': {}
        }
        
        # Test data
        self.test_shops = [
            f"test-shop-{i}.myshopify.com" for i in range(1, 21)
        ]
        self.test_tokens = [
            f"shpat_test_token_{i:04d}" for i in range(1, 21)
        ]

    def log_result(self, endpoint, success, response_time, error=None):
        """Log test result"""
        self.results['total_requests'] += 1
        if success:
            self.results['successful_requests'] += 1
        else:
            self.results['failed_requests'] += 1
            if error:
                self.results['errors'].append(f"{endpoint}: {error}")
        
        self.results['response_times'].append(response_time)
        
        if endpoint not in self.results['endpoint_stats']:
            self.results['endpoint_stats'][endpoint] = {
                'total': 0, 'success': 0, 'fail': 0, 'avg_time': 0
            }
        
        stats = self.results['endpoint_stats'][endpoint]
        stats['total'] += 1
        if success:
            stats['success'] += 1
        else:
            stats['fail'] += 1
        
        # Update average response time
        stats['avg_time'] = (stats['avg_time'] * (stats['total'] - 1) + response_time) / stats['total']

    def make_request(self, method, endpoint, **kwargs):
        """Make HTTP request with timing"""
        start_time = time.time()
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.request(method, url, timeout=30, **kwargs)
            response_time = time.time() - start_time
            
            success = response.status_code < 400
            self.log_result(endpoint, success, response_time)
            
            return response, response_time
        except Exception as e:
            response_time = time.time() - start_time
            self.log_result(endpoint, False, response_time, str(e))
            return None, response_time

    # Core Functionality Tests
    def test_dashboard_load(self):
        """Test dashboard loading under stress"""
        shop = random.choice(self.test_shops)
        host = "test-host"
        
        params = {'shop': shop, 'host': host}
        response, _ = self.make_request('GET', '/dashboard', params=params)
        return response is not None and response.status_code == 200

    def test_health_check(self):
        """Test health endpoint"""
        response, _ = self.make_request('GET', '/health')
        return response is not None and response.status_code == 200

    def test_shopify_settings(self):
        """Test Shopify settings page"""
        shop = random.choice(self.test_shops)
        host = "test-host"
        
        params = {'shop': shop, 'host': host}
        response, _ = self.make_request('GET', '/settings/shopify', params=params)
        return response is not None

    def test_api_process_orders(self):
        """Test order processing API"""
        headers = {
            'Authorization': f'Bearer test-token-{random.randint(1, 100)}',
            'Content-Type': 'application/json'
        }
        response, _ = self.make_request('POST', '/api/process_orders', headers=headers)
        return response is not None

    def test_api_update_inventory(self):
        """Test inventory update API"""
        headers = {
            'Authorization': f'Bearer test-token-{random.randint(1, 100)}',
            'Content-Type': 'application/json'
        }
        response, _ = self.make_request('POST', '/api/update_inventory', headers=headers)
        return response is not None

    def test_api_generate_report(self):
        """Test report generation API"""
        headers = {
            'Authorization': f'Bearer test-token-{random.randint(1, 100)}',
            'Content-Type': 'application/json'
        }
        response, _ = self.make_request('POST', '/api/generate_report', headers=headers)
        return response is not None

    def test_comprehensive_dashboard(self):
        """Test comprehensive dashboard API"""
        headers = {
            'Authorization': f'Bearer test-token-{random.randint(1, 100)}',
            'Content-Type': 'application/json'
        }
        response, _ = self.make_request('GET', '/api/dashboard/comprehensive', headers=headers)
        return response is not None

    def test_csv_exports(self):
        """Test CSV export endpoints"""
        endpoints = [
            '/api/export/inventory',
            '/api/export/orders', 
            '/api/export/revenue'
        ]
        
        headers = {
            'Authorization': f'Bearer test-token-{random.randint(1, 100)}'
        }
        
        endpoint = random.choice(endpoints)
        params = {
            'days': random.choice([7, 30, 90]),
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        
        response, _ = self.make_request('GET', endpoint, headers=headers, params=params)
        return response is not None

    def test_scheduled_reports(self):
        """Test scheduled reports functionality"""
        headers = {
            'Authorization': f'Bearer test-token-{random.randint(1, 100)}',
            'Content-Type': 'application/json'
        }
        
        # Test list
        response, _ = self.make_request('GET', '/api/scheduled-reports', headers=headers)
        
        # Test create
        data = {
            'report_type': random.choice(['orders', 'inventory', 'revenue']),
            'frequency': random.choice(['daily', 'weekly', 'monthly']),
            'delivery_email': f'test{random.randint(1, 1000)}@example.com'
        }
        response, _ = self.make_request('POST', '/api/scheduled-reports', 
                                     headers=headers, json=data)
        
        return response is not None

    def test_shopify_connect_disconnect(self):
        """Test Shopify store connection/disconnection"""
        shop = random.choice(self.test_shops)
        host = "test-host"
        
        # Test connect
        data = {
            'shop_url': shop,
            'access_token': random.choice(self.test_tokens),
            'shop': shop,
            'host': host
        }
        response, _ = self.make_request('POST', '/settings/shopify/connect', data=data)
        
        # Test disconnect
        response, _ = self.make_request('POST', '/settings/shopify/disconnect', data=data)
        
        return response is not None

    def test_static_resources(self):
        """Test static resource loading"""
        static_endpoints = [
            '/favicon.ico',
            '/apple-touch-icon.png',
            '/static/css/dashboard.css',
            '/static/js/app.js'
        ]
        
        endpoint = random.choice(static_endpoints)
        response, _ = self.make_request('GET', endpoint)
        return response is not None

    def test_error_endpoints(self):
        """Test error handling endpoints"""
        response, _ = self.make_request('GET', '/nonexistent-endpoint')
        return response is not None  # Should return 404, which is expected

    def test_api_log_error(self):
        """Test frontend error logging"""
        error_data = {
            'error_type': 'JavaScriptError',
            'error_message': f'Test error {random.randint(1, 1000)}',
            'error_location': 'stress_test.js:1',
            'user_agent': 'StressTest/1.0',
            'timestamp': datetime.now().isoformat()
        }
        
        response, _ = self.make_request('POST', '/api/log_error', json=error_data)
        return response is not None

    # Load Testing Functions
    def run_concurrent_test(self, test_func, num_requests=100):
        """Run a test function concurrently"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(test_func) for _ in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        return results

    def stress_test_all_endpoints(self, requests_per_endpoint=50):
        """Stress test all major endpoints"""
        print("🚀 Starting comprehensive stress test...")
        
        test_functions = [
            ('Dashboard Load', self.test_dashboard_load),
            ('Health Check', self.test_health_check),
            ('Shopify Settings', self.test_shopify_settings),
            ('Process Orders API', self.test_api_process_orders),
            ('Update Inventory API', self.test_api_update_inventory),
            ('Generate Report API', self.test_api_generate_report),
            ('Comprehensive Dashboard API', self.test_comprehensive_dashboard),
            ('CSV Exports', self.test_csv_exports),
            ('Scheduled Reports', self.test_scheduled_reports),
            ('Shopify Connect/Disconnect', self.test_shopify_connect_disconnect),
            ('Static Resources', self.test_static_resources),
            ('Error Handling', self.test_error_endpoints),
            ('Error Logging API', self.test_api_log_error),
        ]
        
        for test_name, test_func in test_functions:
            print(f"\n📊 Testing {test_name} with {requests_per_endpoint} concurrent requests...")
            start_time = time.time()
            
            results = self.run_concurrent_test(test_func, requests_per_endpoint)
            
            end_time = time.time()
            success_rate = (sum(results) / len(results)) * 100 if results else 0
            
            print(f"   ✅ Success Rate: {success_rate:.1f}%")
            print(f"   ⏱️  Duration: {end_time - start_time:.2f}s")
            print(f"   🔥 Requests/sec: {len(results) / (end_time - start_time):.1f}")

    def memory_stress_test(self, duration_minutes=5):
        """Test memory usage under sustained load"""
        print(f"\n🧠 Starting {duration_minutes}-minute memory stress test...")
        
        end_time = time.time() + (duration_minutes * 60)
        request_count = 0
        
        while time.time() < end_time:
            # Rotate through different endpoints
            test_funcs = [
                self.test_dashboard_load,
                self.test_api_process_orders,
                self.test_api_update_inventory,
                self.test_comprehensive_dashboard,
                self.test_health_check
            ]
            
            test_func = random.choice(test_funcs)
            test_func()
            request_count += 1
            
            # Brief pause to prevent overwhelming
            time.sleep(0.1)
        
        print(f"   📈 Total requests: {request_count}")
        print(f"   ⚡ Avg requests/sec: {request_count / (duration_minutes * 60):.1f}")

    def database_stress_test(self, num_operations=1000):
        """Stress test database operations"""
        print(f"\n🗄️  Starting database stress test with {num_operations} operations...")
        
        # Test operations that hit the database heavily
        database_heavy_tests = [
            self.test_comprehensive_dashboard,
            self.test_scheduled_reports,
            self.test_shopify_connect_disconnect,
            self.test_dashboard_load
        ]
        
        results = []
        for _ in range(num_operations):
            test_func = random.choice(database_heavy_tests)
            result = test_func()
            results.append(result)
        
        success_rate = (sum(results) / len(results)) * 100 if results else 0
        print(f"   ✅ Database operations success rate: {success_rate:.1f}%")

    def error_recovery_test(self):
        """Test error handling and recovery"""
        print("\n🛡️  Testing error recovery...")
        
        # Test with invalid data
        invalid_tests = [
            lambda: self.make_request('GET', '/nonexistent-endpoint'),
            lambda: self.make_request('POST', '/api/process_orders', 
                                    headers={'Authorization': 'Bearer invalid-token'}),
            lambda: self.make_request('POST', '/settings/shopify/connect', 
                                    data={'shop_url': 'invalid-shop', 'access_token': 'invalid'}),
            lambda: self.make_request('GET', '/api/export/inventory',
                                    headers={'Authorization': 'Bearer expired-token'}),
            lambda: self.make_request('POST', '/api/scheduled-reports',
                                    json={'invalid': 'data'}),
        ]
        
        for test in invalid_tests:
            test()
        
        print("   ✅ Error recovery tests completed")

    def concurrent_user_simulation(self, num_users=20, duration_minutes=3):
        """Simulate multiple users using the app simultaneously"""
        print(f"\n👥 Simulating {num_users} concurrent users for {duration_minutes} minutes...")
        
        def simulate_user_session():
            """Simulate a typical user session"""
            user_actions = [
                self.test_dashboard_load,
                self.test_health_check,
                self.test_shopify_settings,
                self.test_api_process_orders,
                self.test_csv_exports,
                self.test_comprehensive_dashboard,
            ]
            
            end_time = time.time() + (duration_minutes * 60)
            actions_performed = 0
            
            while time.time() < end_time:
                action = random.choice(user_actions)
                action()
                actions_performed += 1
                
                # Simulate user think time
                time.sleep(random.uniform(1, 5))
            
            return actions_performed
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(simulate_user_session) for _ in range(num_users)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_actions = sum(results)
        print(f"   📊 Total user actions: {total_actions}")
        print(f"   👤 Avg actions per user: {total_actions / num_users:.1f}")

    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("📊 STRESS TEST RESULTS")
        print("="*60)
        
        total_requests = self.results['total_requests']
        success_rate = (self.results['successful_requests'] / total_requests * 100) if total_requests > 0 else 0
        
        print(f"Total Requests: {total_requests}")
        print(f"Successful: {self.results['successful_requests']} ({success_rate:.1f}%)")
        print(f"Failed: {self.results['failed_requests']}")
        
        if self.results['response_times']:
            avg_response_time = sum(self.results['response_times']) / len(self.results['response_times'])
            max_response_time = max(self.results['response_times'])
            min_response_time = min(self.results['response_times'])
            
            # Calculate percentiles
            sorted_times = sorted(self.results['response_times'])
            p95_index = int(len(sorted_times) * 0.95)
            p99_index = int(len(sorted_times) * 0.99)
            
            print(f"\nResponse Times:")
            print(f"  Average: {avg_response_time:.3f}s")
            print(f"  Maximum: {max_response_time:.3f}s")
            print(f"  Minimum: {min_response_time:.3f}s")
            print(f"  95th percentile: {sorted_times[p95_index]:.3f}s")
            print(f"  99th percentile: {sorted_times[p99_index]:.3f}s")
        
        print(f"\nEndpoint Performance:")
        for endpoint, stats in self.results['endpoint_stats'].items():
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {endpoint}: {success_rate:.1f}% success, {stats['avg_time']:.3f}s avg")
        
        if self.results['errors']:
            print(f"\nTop Errors:")
            error_counts = {}
            for error in self.results['errors'][:20]:  # Show top 20
                error_counts[error] = error_counts.get(error, 0) + 1
            
            for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {count}x: {error}")
        
        # Performance recommendations
        print(f"\n🎯 RECOMMENDATIONS:")
        if self.results['response_times'] and avg_response_time > 2.0:
            print("  ⚠️  High response times detected - consider caching or optimization")
        if success_rate < 95:
            print("  ⚠️  Low success rate - check error handling and validation")
        if self.results['failed_requests'] > total_requests * 0.1:
            print("  ⚠️  High error rate - review error logs and fix critical issues")
        if total_requests > 1000 and avg_response_time > 1.0:
            print("  💡 Consider implementing response caching for better performance")
        if success_rate > 98 and avg_response_time < 0.5:
            print("  ✅ Excellent performance! Your app handles load very well")
        
        print("\n✅ Stress test completed!")

def run_full_stress_test():
    """Run the complete stress test suite"""
    tester = EmployeeSuiteStressTest()
    
    # Run all stress tests
    tester.stress_test_all_endpoints(requests_per_endpoint=25)
    tester.memory_stress_test(duration_minutes=2)
    tester.database_stress_test(num_operations=100)
    tester.concurrent_user_simulation(num_users=10, duration_minutes=2)
    tester.error_recovery_test()
    
    # Generate final report
    tester.generate_report()

if __name__ == "__main__":
    run_full_stress_test()
