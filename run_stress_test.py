#!/usr/bin/env python3
"""
Quick Employee Suite Stress Test Runner
"""

import os
import sys
from stress_test import EmployeeSuiteStressTest

def main():
    print("🚀 Employee Suite Stress Test")
    print("=" * 50)
    
    # Get app URL from command line or environment
    app_url = 'http://localhost:5000'
    if len(sys.argv) > 1:
        app_url = sys.argv[1]
    elif os.getenv('APP_URL'):
        app_url = os.getenv('APP_URL')
    
    print(f"Testing: {app_url}")
    print("Press Ctrl+C to stop early\n")
    
    try:
        # Quick test version
        tester = EmployeeSuiteStressTest(base_url=app_url, max_workers=30)
        
        # Setup
        tester.setup_test_data()
        
        # Quick tests
        print("🔥 Quick Stress Test (2 minutes)")
        tester.stress_test_all_endpoints(requests_per_endpoint=15)
        tester.memory_stress_test(duration_minutes=1)
        tester.database_stress_test(num_operations=100)
        
        # Report
        tester.generate_report()
        
    except KeyboardInterrupt:
        print("\n⏹️  Test stopped by user")
        if 'tester' in locals():
            tester.generate_report()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
