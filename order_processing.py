from shopify_integration import ShopifyClient
from flask_login import current_user
from models import ShopifyStore

def process_orders(creds_path='creds.json'):
    try:
        if not current_user.is_authenticated:
            return "⚠️ Please log in first."
        
        store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
        
        if not store:
            return "⚠️ No Shopify store connected. Go to Settings to connect your store."
        
        client = ShopifyClient(store.shop_url, store.access_token)
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
