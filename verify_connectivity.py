from app import app
import unittest
import json

class ConnectivityTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_api_process_orders_no_auth(self):
        """Test process_orders without auth returns 401, not 500"""
        print("Testing /api/process_orders without auth...")
        response = self.client.post('/api/process_orders')
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.data.decode('utf-8')}")
        self.assertEqual(response.status_code, 401)

    def test_api_update_inventory_no_auth(self):
        """Test update_inventory without auth returns 401, not 500"""
        print("Testing /api/update_inventory without auth...")
        response = self.client.post('/api/update_inventory')
        print(f"Status Code: {response.status_code}")
        self.assertEqual(response.status_code, 401)

    def test_api_generate_report_no_auth(self):
        """Test generate_report without auth returns 401, not 500"""
        print("Testing /api/generate_report without auth...")
        response = self.client.post('/api/generate_report')
        print(f"Status Code: {response.status_code}")
        self.assertEqual(response.status_code, 401)

if __name__ == '__main__':
    unittest.main()
