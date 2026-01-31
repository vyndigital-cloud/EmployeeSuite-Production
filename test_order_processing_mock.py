
import unittest
from unittest.mock import MagicMock, patch
from order_processing import process_orders
from flask import Flask

class TestOrderProcessing(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user_patcher = patch('order_processing.current_user')
        self.mock_user = self.user_patcher.start()
        self.mock_user.is_authenticated = True
        self.mock_user.id = 1
        self.mock_user.get_id.return_value = '1'

    def tearDown(self):
        self.user_patcher.stop()
        self.ctx.pop()

    @patch('order_processing.ShopifyStore')
    @patch('shopify_graphql.ShopifyGraphQLClient')
    def test_process_orders_graphql(self, MockClient, MockStore):
        # Setup Mock Store
        mock_store_instance = MagicMock()
        mock_store_instance.shop_url = 'test.myshopify.com'
        mock_store_instance.get_access_token.return_value = 'fake_token'
        MockStore.query.filter_by.return_value.first.return_value = mock_store_instance

        # Setup Mock GraphQL Client
        mock_client_instance = MockClient.return_value
        mock_client_instance.execute_query.return_value = {
            'data': {
                'orders': {
                    'edges': [
                        {
                            'node': {
                                'id': 'gid://shopify/Order/12345',
                                'name': '#1001',
                                'createdAt': '2023-01-01T00:00:00Z',
                                'displayFinancialStatus': 'PENDING',
                                'displayFulfillmentStatus': 'UNFULFILLED',
                                'totalPriceSet': {
                                    'shopMoney': {
                                        'amount': '100.00'
                                    }
                                }
                            }
                        }
                    ],
                    'pageInfo': {
                        'hasNextPage': False
                    }
                }
            }
        }

        # Run process_orders
        result = process_orders(user_id=1)

        # Verify
        print(f"Result: {result}")
        self.assertTrue(result['success'])
        self.assertIn('Pending Orders (1)', result['message'])
        self.assertIn('#1001', result['message'])
        self.assertIn('$100.00', result['message'])

if __name__ == '__main__':
    unittest.main()
