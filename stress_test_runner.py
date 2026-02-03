"""
Stress Test Runner with different test profiles
"""

import argparse
import sys
from stress_test import EmployeeSuiteStressTest

def run_development_test():
    """Light test for development environment"""
    print("🔧 Running Development Stress Test...")
    tester = EmployeeSuiteStressTest(base_url="http://localhost:5000")
    
    tester.stress_test_all_endpoints(requests_per_endpoint=3)
    tester.memory_stress_test(duration_minutes=0.5)
    tester.generate_report()

def run_staging_test():
    """Medium test for staging environment"""
    print("🎭 Running Staging Stress Test...")
    tester = EmployeeSuiteStressTest()
    
    tester.stress_test_all_endpoints(requests_per_endpoint=15)
    tester.memory_stress_test(duration_minutes=2)
    tester.database_stress_test(num_operations=50)
    tester.concurrent_user_simulation(num_users=5, duration_minutes=1)
    tester.error_recovery_test()
    tester.generate_report()

def run_production_test():
    """Heavy test for production environment"""
    print("🚀 Running Production Stress Test...")
    tester = EmployeeSuiteStressTest(max_workers=100)
    
    tester.stress_test_all_endpoints(requests_per_endpoint=50)
    tester.memory_stress_test(duration_minutes=5)
    tester.database_stress_test(num_operations=200)
    tester.concurrent_user_simulation(num_users=20, duration_minutes=3)
    tester.error_recovery_test()
    tester.generate_report()

def run_custom_test(base_url, requests_per_endpoint, duration_minutes, num_users):
    """Run custom stress test with specified parameters"""
    print(f"⚙️  Running Custom Stress Test on {base_url}...")
    tester = EmployeeSuiteStressTest(base_url=base_url)
    
    tester.stress_test_all_endpoints(requests_per_endpoint=requests_per_endpoint)
    tester.memory_stress_test(duration_minutes=duration_minutes)
    tester.concurrent_user_simulation(num_users=num_users, duration_minutes=duration_minutes)
    tester.error_recovery_test()
    tester.generate_report()

def main():
    parser = argparse.ArgumentParser(description='Employee Suite Stress Test Runner')
    parser.add_argument('--profile', choices=['dev', 'staging', 'production'], 
                       default='dev', help='Test profile to run')
    parser.add_argument('--url', default='http://localhost:5000', 
                       help='Base URL to test')
    parser.add_argument('--requests', type=int, default=10, 
                       help='Requests per endpoint for custom test')
    parser.add_argument('--duration', type=int, default=2, 
                       help='Duration in minutes for custom test')
    parser.add_argument('--users', type=int, default=5, 
                       help='Number of concurrent users for custom test')
    parser.add_argument('--custom', action='store_true', 
                       help='Run custom test with specified parameters')
    
    args = parser.parse_args()
    
    if args.custom:
        run_custom_test(args.url, args.requests, args.duration, args.users)
    elif args.profile == 'dev':
        run_development_test()
    elif args.profile == 'staging':
        run_staging_test()
    elif args.profile == 'production':
        run_production_test()

if __name__ == "__main__":
    main()
