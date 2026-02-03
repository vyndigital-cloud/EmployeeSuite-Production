"""
Quick Stress Test - Run this for fast validation
"""

import requests
import time
import concurrent.futures
from stress_test import EmployeeSuiteStressTest

def quick_test():
    """Run a quick 2-minute stress test"""
    print("🚀 Running Quick Stress Test (2 minutes)...")
    print("This will test core functionality with lighter load")
    
    tester = EmployeeSuiteStressTest()
    
    # Quick test with fewer requests
    print("\n📊 Testing core endpoints...")
    tester.stress_test_all_endpoints(requests_per_endpoint=5)
    
    print("\n🧠 Testing memory under light load...")
    tester.memory_stress_test(duration_minutes=1)
    
    print("\n👥 Simulating concurrent users...")
    tester.concurrent_user_simulation(num_users=3, duration_minutes=1)
    
    print("\n🛡️ Testing error handling...")
    tester.error_recovery_test()
    
    tester.generate_report()

def micro_test():
    """Run a 30-second micro test for development"""
    print("⚡ Running Micro Stress Test (30 seconds)...")
    
    tester = EmployeeSuiteStressTest()
    
    # Test only critical endpoints
    critical_tests = [
        ('Health Check', tester.test_health_check),
        ('Dashboard Load', tester.test_dashboard_load),
        ('API Process Orders', tester.test_api_process_orders),
    ]
    
    for test_name, test_func in critical_tests:
        print(f"\n🔥 Testing {test_name}...")
        results = tester.run_concurrent_test(test_func, 3)
        success_rate = (sum(results) / len(results)) * 100 if results else 0
        print(f"   Success Rate: {success_rate:.1f}%")
    
    tester.generate_report()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "micro":
        micro_test()
    else:
        quick_test()
