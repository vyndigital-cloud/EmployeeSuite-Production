import requests
import os

class ShopifyClient:
    def __init__(self, shop_url, access_token):
        self.shop_url = shop_url.replace('https://', '').replace('http://', '')
        self.access_token = access_token
        self.api_version = "2024-01"
        
    def _get_headers(self):
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }
    
    def _make_request(self, endpoint):
        url = f"https://{self.shop_url}/admin/api/{self.api_version}/{endpoint}"
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def get_products(self):
        data = self._make_request("products.json")
        if "error" in data:
            return {"error": data["error"]}
        inventory = []
        for product in data.get('products', []):
            for variant in product.get('variants', []):
                inventory.append({
                    'product': product['title'],
                    'sku': variant.get('sku', 'N/A'),
                    'stock': variant.get('inventory_quantity', 0),
                    'price': f"${variant.get('price', '0')}"
                })
        return inventory
    
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
