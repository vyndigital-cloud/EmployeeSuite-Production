import unittest
from unittest.mock import MagicMock, patch
from reporting import generate_report
from models import User, ShopifyStore

class TestReportingMock(unittest.TestCase):

    def setUp(self):
        self.mock_user = MagicMock(spec=User)
        self.mock_user.id = 1
        self.mock_user.is_authenticated = True
        
        self.mock_store = MagicMock(spec=ShopifyStore)
        self.mock_store.shop_url = "test-store.myshopify.com"
        self.mock_store.user_id = 1
        self.mock_store.is_active = True
        self.mock_store.get_access_token.return_value = "shpat_123456"

    @patch('reporting.ShopifyStore')
    @patch('reporting.current_user')
    @patch('shopify_graphql.ShopifyGraphQLClient')
    def test_generate_report_auth_error(self, mock_client_class, mock_current_user, mock_store_cls):
        # Setup mocks
        mock_current_user.is_authenticated = True
        mock_current_user.id = 1
        
        mock_store_cls.query.filter_by.return_value.first.return_value = self.mock_store
        
        # Mock GraphQL client to return Auth Error
        mock_client = mock_client_class.return_value
        mock_client.get_orders.return_value = {'error': '401 Unauthorized'}
        
        # Run function
        result = generate_report(user_id=1)
        
        # Assertions
        self.assertFalse(result['success'])
        self.assertIn("Authentication Issue", result['error'])
        # Verify we didn't crash
        self.assertTrue(self.mock_store.is_active) # Should still be true (no auto-disable)

    @patch('reporting.ShopifyStore')
    @patch('reporting.current_user')
    @patch('shopify_graphql.ShopifyGraphQLClient')
    def test_generate_report_generic_error(self, mock_client_class, mock_current_user, mock_store_cls):
        # Setup mocks
        mock_current_user.is_authenticated = True
        mock_current_user.id = 1
        
        mock_store_cls.query.filter_by.return_value.first.return_value = self.mock_store
        
        # Mock GraphQL client to return Generic Error
        mock_client = mock_client_class.return_value
        mock_client.get_orders.return_value = {'error': 'Internal Server Error'}
        
        # Run function
        result = generate_report(user_id=1)
        
        # Assertions
        self.assertFalse(result['success'])
        # Verify it contains the standard error header which prevents "Connection Error" on frontend
        self.assertIn("Error Loading revenue", result['error'])
        self.assertIn("Internal Server Error", result['error'])

    @patch('reporting.ShopifyStore')
    @patch('reporting.current_user')
    @patch('shopify_graphql.ShopifyGraphQLClient')
    def test_generate_report_success(self, mock_client_class, mock_current_user, mock_store_cls):
        # Setup mocks
        mock_current_user.is_authenticated = True
        mock_current_user.id = 1
        mock_store_cls.query.filter_by.return_value.first.return_value = self.mock_store
        
        # Mock GraphQL client to return Orders
        mock_client = mock_client_class.return_value
        mock_client.get_orders.side_effect = [
            {
                'orders': {
                    'edges': [
                        {
                            'node': {
                                'displayFinancialStatus': 'PAID',
                                'totalPriceSet': {'shopMoney': {'amount': '100.00'}},
                                'lineItems': {'edges': [{'node': {'title': 'Test Product', 'quantity': 1, 'originalUnitPriceSet': {'shopMoney': {'amount': '100.00'}} }}]}
                            }
                        }
                    ],
                    'pageInfo': {'hasNextPage': False}
                }
            }
        ]
        
        # Run function
        result = generate_report(user_id=1)
        
        # Assertions
        self.assertTrue(result['success'])
        self.assertIn("$100.00", result['message'])

if __name__ == '__main__':
    unittest.main()
