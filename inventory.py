from flask_login import current_user
from models import ShopifyStore
from shopify_integration import ShopifyClient

def check_inventory():
    """Check inventory levels and return low stock alerts"""
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    
    if not store:
        return {"success": False, "error": "No Shopify store connected"}
    
    try:
        client = ShopifyClient(store.shop_url, store.access_token)
        products = client.get_products()
        
        low_stock_items = []
        threshold = 10
        
        for product in products:
            inventory = product.get('inventory_quantity', 0)
            if inventory < threshold:
                low_stock_items.append({
                    'title': product.get('title', 'Unknown'),
                    'inventory': inventory,
                    'id': product.get('id')
                })
        
        if low_stock_items:
            message = "<div style='margin: 16px 0;'><h4 style='font-size: 15px; font-weight: 600; color: #171717; margin-bottom: 12px;'>Low Stock Alerts</h4>"
            for item in low_stock_items:
                alert_color = '#dc2626' if item['inventory'] == 0 else '#f59e0b'
                message += f"""
                <div style='padding: 12px; margin: 8px 0; background: #fafafa; border-radius: 6px; border-left: 3px solid {alert_color};'>
                    <div style='font-weight: 500; color: #171717; font-size: 14px;'>{item.get('title', 'Unknown Product')}</div>
                    <div style='color: #737373; margin-top: 4px; font-size: 13px;'>Stock: {item['inventory']} units (below threshold of {threshold})</div>
                </div>
                """
            message += "</div>"
            return {"success": True, "message": message}
        else:
            return {"success": True, "message": "<div style='padding: 16px; background: #f0fdf4; border-radius: 6px; border-left: 3px solid #16a34a; color: #166534; font-size: 14px;'>All products have sufficient stock</div>"}
    
    except Exception as e:
        return {"success": False, "error": f"Error checking inventory: {str(e)}"}

def update_inventory():
    """Update inventory - wrapper for check_inventory"""
    return check_inventory()
