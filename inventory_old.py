from shopify_integration import ShopifyClient
from flask_login import current_user
from models import ShopifyStore

def update_inventory():
    try:
        if not current_user.is_authenticated:
            return "⚠️ Please log in first."
        
        store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
        
        if not store:
            return "⚠️ No Shopify store connected. Go to Settings to connect your store."
        
        client = ShopifyClient(store.shop_url, store.access_token)
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
