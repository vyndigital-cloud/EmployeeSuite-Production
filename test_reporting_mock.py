
import unittest
from unittest.mock import MagicMock, patch
from reporting import generate_report
from flask import Flask

class TestReporting(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user_patcher = patch('reporting.current_user')
        self.mock_user = self.user_patcher.start()
        self.mock_user.is_authenticated = True
        self.mock_user.id = 1
        self.mock_user.get_id.return_value = '1'

    def tearDown(self):
        self.user_patcher.stop()
        self.ctx.pop()

    @patch('reporting.ShopifyStore')
    @patch('shopify_graphql.ShopifyGraphQLClient')
    def test_generate_report(self, MockClient, MockStore):
        # Setup Mock Store
        mock_store_instance = MagicMock()
        mock_store_instance.shop_url = 'test.myshopify.com'
        mock_store_instance.get_access_token.return_value = 'fake_token'
        mock_store_instance.user_id = 1
        MockStore.query.filter_by.return_value.first.return_value = mock_store_instance

        # Setup Mock GraphQL Client
        mock_client_instance = MockClient.return_value
        # Mock get_orders response
        mock_client_instance.get_orders.return_value = {
            'orders': {
                'edges': [
                    {
                        'node': {
                            'id': 'gid://shopify/Order/1',
                            'displayFinancialStatus': 'PAID',
                            'totalPriceSet': {'shopMoney': {'amount': '50.00'}},
                            'lineItems': {
                                'edges': [
                                    {
                                        'node': {
                                            'title': 'Test Product',
                                            'quantity': 1,
                                            'originalUnitPriceSet': {'shopMoney': {'amount': '50.00'}}
                                        }
                                    }
                                ]
                            }
                        }
                    }
                ],
                'pageInfo': {'hasNextPage': False}
            }
        }

        # Run generate_report
        result = generate_report(user_id=1)

        # Verify
        print(f"Result: {result}")
        self.assertTrue(result['success'])
        self.assertIn('$50.00', result['message'])
        self.assertIn('Test Product', result['message'])
        self.assertEqual(result['report_data']['total_revenue'], 50.0)

if __name__ == '__main__':
    unittest.main()
