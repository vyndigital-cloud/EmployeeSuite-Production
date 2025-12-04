from flask_login import current_user
from models import ShopifyStore
from shopify_integration import ShopifyClient
import requests

def check_inventory():
    """Check inventory levels and return low stock alerts"""
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    
    if not store:
        return {"success": False, "error": "No Shopify store connected. Go to Settings to connect."}
    
    try:
        client = ShopifyClient(store.shop_url, store.access_token)
        
        # Get products with error handling
        try:
            products = client.get_products()
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Shopify API timeout. Please try again in a moment."}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Cannot connect to Shopify. Check your internet connection."}
        except Exception as e:
            return {"success": False, "error": f"Shopify API error: {str(e)}"}
        
        # Check if products returned an error
        if isinstance(products, dict) and "error" in products:
            return {"success": False, "error": f"Shopify returned an error: {products['error']}"}
        
        if not products or len(products) == 0:
            return {"success": True, "message": "<div style='padding: 16px; background: #fffbeb; border-radius: 6px; border-left: 3px solid #f59e0b; color: #92400e; font-size: 14px;'>⚠️ No products found in your store.</div>"}
        
        low_stock_items = []
        threshold = 10
        
        for product in products:
            inventory = product.get('stock', 0)
            if inventory < threshold:
                low_stock_items.append({
                    'title': product.get('product', 'Unknown Product'),
                    'inventory': inventory,
                    'id': product.get('sku', 'N/A')
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
            return {"success": True, "message": "<div style='padding: 16px; background: #f0fdf4; border-radius: 6px; border-left: 3px solid #16a34a; color: #166534; font-size: 14px;'>✅ All products have sufficient stock</div>"}
    
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}

def update_inventory():
    """Update inventory - wrapper for check_inventory"""
    return check_inventory()
