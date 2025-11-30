from shopify_integration import ShopifyClient
import os
from dotenv import load_dotenv

load_dotenv()

def process_orders(creds_path='creds.json'):
    try:
        SHOP_URL = os.getenv('SHOPIFY_URL')
        ACCESS_TOKEN = os.getenv('SHOPIFY_TOKEN')
        if not ACCESS_TOKEN:
            return "⚠️ Shopify not configured. Add credentials in settings."
        client = ShopifyClient(SHOP_URL, ACCESS_TOKEN)
        orders = client.get_orders()
        if isinstance(orders, dict) and "error" in orders:
            return f"❌ Error: {orders['error']}"
        if len(orders) == 0:
            return "✅ No pending orders. All caught up!"
        return f"✅ Processed {len(orders)} Shopify orders successfully"
    except Exception as e:
        return f"❌ Error processing orders: {str(e)}"

if __name__ == "__main__":
    result = process_orders()
    print(f"Result: {result}")
