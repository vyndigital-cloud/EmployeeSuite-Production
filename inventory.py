from shopify_integration import ShopifyClient
import os
from dotenv import load_dotenv

load_dotenv()

def update_inventory():
    try:
        SHOP_URL = os.getenv('SHOPIFY_URL')
        ACCESS_TOKEN = os.getenv('SHOPIFY_TOKEN')
        if not ACCESS_TOKEN:
            return "⚠️ Shopify not configured. Add credentials in settings."
        client = ShopifyClient(SHOP_URL, ACCESS_TOKEN)
        low_stock = client.get_low_stock(threshold=10)
        if isinstance(low_stock, dict) and "error" in low_stock:
            return f"❌ Error: {low_stock['error']}"
        if len(low_stock) == 0:
            all_products = client.get_products()
            total = len(all_products) if not isinstance(all_products, dict) else 0
            return f"✅ All inventory levels healthy! {total} products in stock."
        alerts = []
        for item in low_stock:
            alerts.append(f"🚨 {item['product']}: Only {item['stock']} units left")
        return "\n".join(alerts)
    except Exception as e:
        return f"❌ Error checking inventory: {str(e)}"

if __name__ == "__main__":
    result = update_inventory()
    print(f"Result: {result}")
