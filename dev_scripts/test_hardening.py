import unittest
from shopify_utils import parse_gid, format_gid, safe_int

class TestShopifyUtils(unittest.TestCase):
    
    def test_parse_gid_valid_string(self):
        self.assertEqual(parse_gid("gid://shopify/Shop/123456"), 123456)
        self.assertEqual(parse_gid("gid://shopify/AppSubscription/987654321"), 987654321)
        
    def test_parse_gid_numeric_string(self):
        self.assertEqual(parse_gid("123456"), 123456)
        
    def test_parse_gid_int(self):
        self.assertEqual(parse_gid(123456), 123456)
        
    def test_parse_gid_with_query_params(self):
        self.assertEqual(parse_gid("gid://shopify/Shop/123456?some=param"), 123456)
        
    def test_parse_gid_invalid(self):
        self.assertIsNone(parse_gid(None))
        self.assertIsNone(parse_gid(""))
        self.assertIsNone(parse_gid("invalid-gid"))
        self.assertIsNone(parse_gid("gid://shopify/Shop/NaN"))
        
    def test_format_gid(self):
        self.assertEqual(format_gid(12345, 'Shop'), "gid://shopify/Shop/12345")
        self.assertEqual(format_gid('67890', 'Product'), "gid://shopify/Product/67890")
        
    def test_safe_int(self):
        self.assertEqual(safe_int("123"), 123)
        self.assertEqual(safe_int(123), 123)
        self.assertIsNone(safe_int("abc"))
        self.assertIsNone(safe_int(None))
        self.assertEqual(safe_int("abc", default=0), 0)

if __name__ == '__main__':
    unittest.main()
