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
        
        # Get ONLY unfulfilled/pending orders that need action
        # Filter for: financial_status=pending OR fulfillment_status=unfulfilled
        try:
            # Fetch orders with pending payment status
            pending_orders_data = client._make_request("orders.json?financial_status=pending&limit=250")
            # Fetch orders that are paid but unfulfilled
            unfulfilled_orders_data = client._make_request("orders.json?financial_status=paid&fulfillment_status=unfulfilled&limit=250")
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Shopify API timeout. Please try again in a moment."}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Cannot connect to Shopify. Check your internet connection."}
        except Exception as e:
            return {"success": False, "error": f"Shopify API error: {str(e)}"}
        
        # Combine and deduplicate orders
        all_orders = []
        order_ids = set()
        
        if "error" not in pending_orders_data:
            for order in pending_orders_data.get('orders', []):
                if order.get('id') not in order_ids:
                    all_orders.append(order)
                    order_ids.add(order.get('id'))
        
        if "error" not in unfulfilled_orders_data:
            for order in unfulfilled_orders_data.get('orders', []):
                if order.get('id') not in order_ids:
                    all_orders.append(order)
                    order_ids.add(order.get('id'))
        
        if len(all_orders) == 0:
            return {"success": True, "message": "<div style='padding: 16px; background: #f0fdf4; border-radius: 6px; border-left: 3px solid #16a34a; color: #166534; font-size: 14px;'>✅ No pending orders. All caught up!</div>"}
        
        # Build clean HTML output with real-time timestamp
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        html = f"<div style='margin: 16px 0;'><h4 style='font-size: 15px; font-weight: 600; color: #171717; margin-bottom: 12px;'>Pending Orders ({len(all_orders)})</h4>"
        html += "<div style='font-size: 13px; color: #737373; margin-bottom: 12px;'>Showing orders that need action: pending payment or unfulfilled</div>"
        html += f"<div style='font-size: 12px; color: #737373; margin-bottom: 12px; font-style: italic;'>🔄 Live data fetched: {timestamp}</div>"
        
        for order in all_orders[:50]:  # Show up to 50 orders
            order_name = order.get('name', 'N/A')
            total = order.get('total_price', '0')
            financial_status = order.get('financial_status', 'pending')
            fulfillment_status = order.get('fulfillment_status', 'unfulfilled')
            
            # Determine status and color
            if financial_status == 'pending':
                status_text = "Pending Payment"
                status_color = '#f59e0b'
            elif fulfillment_status == 'unfulfilled':
                status_text = "Unfulfilled"
                status_color = '#dc2626'
            else:
                status_text = "Needs Action"
                status_color = '#f59e0b'
            
            html += f"""
            <div style='padding: 14px; margin: 8px 0; background: #fafafa; border-radius: 6px; border-left: 3px solid {status_color};'>
                <div style='font-weight: 500; color: #171717; font-size: 14px;'>Order {order_name}</div>
                <div style='color: #737373; margin-top: 4px; font-size: 13px;'>Total: ${total} • {status_text}</div>
            </div>
            """
        
        html += "</div>"
        
        return {"success": True, "message": html}
        
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
