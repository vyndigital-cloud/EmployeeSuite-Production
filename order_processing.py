from shopify_integration import ShopifyClient
from flask_login import current_user
from models import ShopifyStore
import requests

def process_orders(creds_path='creds.json'):
    try:
        if not current_user.is_authenticated:
            return {"success": False, "error": "Please log in first"}
        
        store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
        
        if not store:
            return {"success": False, "error": "No Shopify store connected. Go to Settings."}
        
        client = ShopifyClient(store.shop_url, store.access_token)
        
        # Get raw Shopify orders with timeout and error handling
        try:
            orders_data = client._make_request("orders.json")
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Shopify API timeout. Please try again in a moment."}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Cannot connect to Shopify. Check your internet connection."}
        except Exception as e:
            return {"success": False, "error": f"Shopify API error: {str(e)}"}
        
        if "error" in orders_data:
            return {"success": False, "error": f"Shopify returned an error: {orders_data['error']}"}
        
        orders = orders_data.get('orders', [])
        
        if len(orders) == 0:
            return {"success": True, "message": "<div style='padding: 16px; background: #f0fdf4; border-radius: 6px; border-left: 3px solid #16a34a; color: #166534; font-size: 14px;'>✅ No pending orders. All caught up!</div>"}
        
        # Build clean HTML output
        html = "<div style='margin: 16px 0;'><h4 style='font-size: 15px; font-weight: 600; color: #171717; margin-bottom: 12px;'>Recent Orders</h4>"
        
        for order in orders[:10]:
            order_name = order.get('name', 'N/A')
            total = order.get('total_price', '0')
            status = order.get('financial_status', 'pending')
            
            status_color = '#16a34a' if status == 'paid' else '#f59e0b'
            
            html += f"""
            <div style='padding: 14px; margin: 8px 0; background: #fafafa; border-radius: 6px; border-left: 3px solid {status_color};'>
                <div style='font-weight: 500; color: #171717; font-size: 14px;'>Order {order_name}</div>
                <div style='color: #737373; margin-top: 4px; font-size: 13px;'>Total: ${total} • Status: {status.title()}</div>
            </div>
            """
        
        html += "</div>"
        
        return {"success": True, "message": html}
        
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
