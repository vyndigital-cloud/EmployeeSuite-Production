# Employee Suite Stress Testing

This directory contains comprehensive stress testing tools for the Employee Suite Shopify app.

## Quick Start

### 1. Install Dependencies
```bash
pip install requests pytest
```

### 2. Run Tests

**Quick Test (2 minutes):**
```bash
python quick_stress_test.py
```

**Micro Test (30 seconds):**
```bash
python quick_stress_test.py micro
```

**Full Stress Test (10-15 minutes):**
```bash
python stress_test.py
```

### 3. Environment-Specific Tests

**Development:**
```bash
python stress_test_runner.py --profile dev
```

**Staging:**
```bash
python stress_test_runner.py --profile staging --url https://your-staging-url.com
```

**Production:**
```bash
python stress_test_runner.py --profile production --url https://your-production-url.com
```

**Custom Test:**
```bash
python stress_test_runner.py --custom --url http://localhost:5000 --requests 25 --duration 3 --users 10
```

## What Gets Tested

### Core Endpoints
- ✅ Dashboard loading (`/dashboard`)
- ✅ Health check (`/health`)
- ✅ Shopify settings (`/settings/shopify`)
- ✅ Static resources (`/favicon.ico`, etc.)

### API Endpoints
- ✅ Process orders (`/api/process_orders`)
- ✅ Update inventory (`/api/update_inventory`)
- ✅ Generate reports (`/api/generate_report`)
- ✅ Comprehensive dashboard (`/api/dashboard/comprehensive`)
- ✅ CSV exports (`/api/export/*`)
- ✅ Scheduled reports (`/api/scheduled-reports`)
- ✅ Error logging (`/api/log_error`)

### Shopify Integration
- ✅ Store connection (`/settings/shopify/connect`)
- ✅ Store disconnection (`/settings/shopify/disconnect`)
- ✅ OAuth flow simulation

### Stress Test Types

1. **Endpoint Stress Test**: Hits each endpoint with concurrent requests
2. **Memory Stress Test**: Sustained load over time to test memory usage
3. **Database Stress Test**: Heavy database operations
4. **Concurrent User Simulation**: Simulates real user behavior
5. **Error Recovery Test**: Tests error handling with invalid data

## Understanding Results

### Success Metrics
- **Success Rate**: Percentage of requests that completed successfully
- **Response Times**: Average, min, max, and percentile response times
- **Requests/Second**: Throughput under load

### Performance Thresholds
- ✅ **Excellent**: >98% success rate, <0.5s avg response time
- ⚠️ **Good**: >95% success rate, <1.0s avg response time  
- ❌ **Needs Work**: <95% success rate, >2.0s avg response time

### Sample Output
```
📊 STRESS TEST RESULTS
============================================================
Total Requests: 650
Successful: 637 (98.0%)
Failed: 13

Response Times:
  Average: 0.245s
  Maximum: 1.234s
  Minimum: 0.089s
  95th percentile: 0.567s
  99th percentile: 0.891s

Endpoint Performance:
  /dashboard: 98.5% success, 0.234s avg
  /health: 100.0% success, 0.123s avg
  /api/process_orders: 96.2% success, 0.456s avg

🎯 RECOMMENDATIONS:
  ✅ Excellent performance! Your app handles load very well
```

## Customizing Tests

### Add New Test Functions
```python
def test_my_endpoint(self):
    """Test custom endpoint"""
    response, _ = self.make_request('GET', '/my-endpoint')
    return response is not None and response.status_code == 200
```

### Modify Test Parameters
Edit `test_config.py` to adjust:
- Number of concurrent requests
- Test duration
- Performance thresholds
- Test data

### Environment Variables
Set these for more realistic testing:
```bash
export SHOPIFY_API_KEY=your_api_key
export SHOPIFY_API_SECRET=your_api_secret
export DATABASE_URL=your_test_db_url
```

## Troubleshooting

### Common Issues

**Connection Errors:**
- Check if your app is running
- Verify the base URL is correct
- Ensure firewall allows connections

**High Error Rates:**
- Check app logs for specific errors
- Verify database connections
- Check API rate limits

**Slow Response Times:**
- Monitor server resources (CPU, memory)
- Check database query performance
- Consider adding caching

### Debug Mode
Add debug logging to see detailed request/response info:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Best Practices

1. **Start Small**: Begin with micro tests, then scale up
2. **Test Regularly**: Run quick tests during development
3. **Monitor Resources**: Watch CPU, memory, and database during tests
4. **Test Realistic Scenarios**: Use actual shop domains and data patterns
5. **Document Results**: Keep track of performance over time

## Integration with CI/CD

Add to your GitHub Actions or deployment pipeline:
```yaml
- name: Run Stress Tests
  run: |
    python quick_stress_test.py micro
    if [ $? -ne 0 ]; then exit 1; fi
```

This ensures performance regressions are caught early!
