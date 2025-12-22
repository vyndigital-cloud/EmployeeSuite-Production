import requests
import os
from performance import cache_result, CACHE_TTL_INVENTORY, CACHE_TTL_ORDERS

class ShopifyClient:
    def __init__(self, shop_url, access_token):
        self.shop_url = shop_url.replace('https://', '').replace('http://', '')
        self.access_token = access_token
        self.api_version = "2024-10"  # Match app.json API version
        
    def _get_headers(self):
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }
    
    def _make_request(self, endpoint):
        url = f"https://{self.shop_url}/admin/api/{self.api_version}/{endpoint}"
        try:
            # Always fetch fresh data - no caching
            # Add cache-control headers to ensure real-time data
            headers = self._get_headers()
            headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            headers['Pragma'] = 'no-cache'
            headers['Expires'] = '0'
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def _make_graphql_request(self, query, variables=None):
        """Make a GraphQL request to Shopify Admin API"""
        url = f"https://{self.shop_url}/admin/api/{self.api_version}/graphql.json"
        headers = self._get_headers()
        headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    @cache_result(ttl=CACHE_TTL_INVENTORY)
    def get_products(self):
        """
        Get products using GraphQL (migrated from deprecated REST API)
        Returns same format as before for backward compatibility
        """
        # GraphQL query to fetch products with variants and inventory
        # Migrated from deprecated REST API /products.json endpoint
        # Using GraphQL Admin API as required by Shopify (deadline: 2025-04-01)
        query = """
        query getProducts($first: Int!, $after: String) {
            products(first: $first, after: $after) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                edges {
                    node {
                        id
                        title
                        variants(first: 250) {
                            edges {
                                node {
                                    id
                                    sku
                                    price
                                    inventoryItem {
                                        id
                                        quantityAvailable
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        inventory = []
        cursor = None
        has_next_page = True
        
        # Paginate through all products
        while has_next_page:
            variables = {"first": 250}  # Max 250 products per request
            if cursor:
                variables["after"] = cursor
            
            data = self._make_graphql_request(query, variables)
            
            if "error" in data:
                return {"error": data["error"]}
            
            if "errors" in data:
                return {"error": str(data["errors"])}
            
            products_data = data.get("data", {}).get("products", {})
            page_info = products_data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")
            
            # Process products
            for edge in products_data.get("edges", []):
                product = edge["node"]
                product_title = product.get("title", "Untitled")
                
                # Process variants
                for variant_edge in product.get("variants", {}).get("edges", []):
                    variant = variant_edge["node"]
                    
                    # Handle None values - Shopify can return None for SKU
                    sku = variant.get("sku") or 'N/A'
                    price_value = variant.get("price") or '0'
                    price = f"${price_value}" if price_value != '0' else 'N/A'
                    
                    # Get inventory quantity from GraphQL structure
                    stock = 0
                    inventory_item = variant.get("inventoryItem")
                    if inventory_item:
                        # Use quantityAvailable (direct field, more reliable)
                        stock = inventory_item.get("quantityAvailable", 0) or 0
                    
                    inventory.append({
                        'product': product_title,
                        'sku': sku,
                        'stock': stock,
                        'price': price
                    })
        
        return inventory
    
    @cache_result(ttl=CACHE_TTL_ORDERS)
    def get_orders(self, status='any', limit=50):
        data = self._make_request(f"orders.json?status={status}&limit={limit}")
        if "error" in data:
            return {"error": data["error"]}
        orders = []
        for order in data.get('orders', []):
            orders.append({
                'id': order['order_number'],
                'customer': order.get('customer', {}).get('email', 'Guest'),
                'total': f"${order['total_price']}",
                'items': len(order['line_items']),
                'status': order.get('financial_status', 'N/A').upper()
            })
        return orders
    
    def get_low_stock(self, threshold=5):
        inventory = self.get_products()
        if isinstance(inventory, dict) and "error" in inventory:
            return inventory
        return [item for item in inventory if item['stock'] < threshold]

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    SHOP_URL = os.getenv('SHOPIFY_URL', 'testsuite-dev.myshopify.com')
    ACCESS_TOKEN = os.getenv('SHOPIFY_TOKEN', '')
    if not ACCESS_TOKEN:
        print("No SHOPIFY_TOKEN found in .env file!")
        exit(1)
    print(f"Testing connection to {SHOP_URL}...")
    client = ShopifyClient(SHOP_URL, ACCESS_TOKEN)
    print("\nTesting inventory...")
    inventory = client.get_products()
    if isinstance(inventory, dict) and "error" in inventory:
        print(f"Error: {inventory['error']}")
    else:
        print(f"Found {len(inventory)} products")
        for item in inventory[:3]:
            print(f"  - {item['product']}: {item['stock']} units at {item['price']}")
    print("\nTesting orders...")
    orders = client.get_orders()
    if isinstance(orders, dict) and "error" in orders:
        print(f"Error: {orders['error']}")
    else:
        print(f"Found {len(orders)} orders")
    print("\nTesting low stock...")
    low_stock = client.get_low_stock(threshold=10)
    if isinstance(low_stock, dict) and "error" in low_stock:
        print(f"Error: {low_stock['error']}")
    else:
        print(f"Found {len(low_stock)} low stock items")
