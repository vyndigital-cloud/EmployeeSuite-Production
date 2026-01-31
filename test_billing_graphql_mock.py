import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from billing import create_recurring_charge, get_charge_status, activate_recurring_charge

class TestBillingGraphQL(unittest.TestCase):
    
    @patch('shopify_graphql.ShopifyGraphQLClient')
    def test_create_recurring_charge(self, mock_client_class):
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock successful response
        mock_client.execute_query.return_value = {
            'appSubscriptionCreate': {
                'appSubscription': {
                    'id': 'gid://shopify/AppSubscription/123456789',
                    'status': 'PENDING'
                },
                'confirmationUrl': 'https://admin.shopify.com/store/test-store/charges/123456/confirm',
                'userErrors': []
            }
        }
        
        # Call function
        result = create_recurring_charge('test-store.myshopify.com', 'test-token', 'https://app-url.com/return')
        
        # Assertions
        self.assertTrue(result['success'])
        self.assertEqual(result['charge_id'], 123456789)
        self.assertEqual(result['status'], 'PENDING')
        self.assertEqual(result['confirmation_url'], 'https://admin.shopify.com/store/test-store/charges/123456/confirm')
        
        # Verify mutation was called
        args, _ = mock_client.execute_query.call_args
        self.assertIn('mutation AppSubscriptionCreate', args[0])
        
    @patch('shopify_graphql.ShopifyGraphQLClient')
    def test_get_charge_status(self, mock_client_class):
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock successful response
        mock_client.execute_query.return_value = {
            'node': {
                'id': 'gid://shopify/AppSubscription/123456789',
                'status': 'ACTIVE'
            }
        }
        
        # Call function
        result = get_charge_status('test-store.myshopify.com', 'test-token', '123456789')
        
        # Assertions
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'active') # Our code converts to lower case
        
        # Verify query was called with correct ID format
        args, kwargs = mock_client.execute_query.call_args
        # args[1] is variables dict
        self.assertEqual(args[1]['id'], 'gid://shopify/AppSubscription/123456789')

    @patch('shopify_graphql.ShopifyGraphQLClient')
    def test_activate_recurring_charge(self, mock_client_class):
        # activate calls get_charge_status internally now
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_client.execute_query.return_value = {
            'node': {
                'id': 'gid://shopify/AppSubscription/123456789',
                'status': 'ACTIVE'
            }
        }
        
        result = activate_recurring_charge('test-store.myshopify.com', 'test-token', '123456789')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'active')

if __name__ == '__main__':
    print("Running GraphQL Billing Mock Tests...")
    unittest.main()
