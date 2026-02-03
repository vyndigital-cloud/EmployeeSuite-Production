"""
Configuration for stress tests
"""

# Test environments
ENVIRONMENTS = {
    'development': {
        'base_url': 'http://localhost:5000',
        'requests_per_endpoint': 5,
        'duration_minutes': 1,
        'concurrent_users': 3,
        'max_workers': 10
    },
    'staging': {
        'base_url': 'https://staging-employee-suite.herokuapp.com',
        'requests_per_endpoint': 20,
        'duration_minutes': 3,
        'concurrent_users': 10,
        'max_workers': 25
    },
    'production': {
        'base_url': 'https://employee-suite.herokuapp.com',
        'requests_per_endpoint': 50,
        'duration_minutes': 5,
        'concurrent_users': 25,
        'max_workers': 50
    }
}

# Test data
TEST_SHOPS = [
    "stress-test-1.myshopify.com",
    "stress-test-2.myshopify.com", 
    "stress-test-3.myshopify.com",
    "load-test-store.myshopify.com",
    "performance-test.myshopify.com"
]

TEST_TOKENS = [
    "shpat_stress_test_token_001",
    "shpat_stress_test_token_002",
    "shpat_stress_test_token_003"
]

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    'max_response_time': 3.0,  # seconds
    'min_success_rate': 95.0,  # percentage
    'max_error_rate': 5.0,     # percentage
    'max_avg_response_time': 1.0  # seconds
}
