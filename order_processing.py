from shopify_integration import ShopifyClient
from flask_login import current_user
from models import ShopifyStore
import requests

def process_orders(creds_path='creds.json', user_id=None):
    # CRITICAL: Accept user_id as parameter to prevent recursion from accessing current_user
    # This prevents "maximum recursion depth exceeded" errors
    # #region agent log
    try:
        import json
        import time
        # Safely check authentication without triggering recursion
        is_authenticated = False
        try:
            is_authenticated = hasattr(current_user, 'is_authenticated') and current_user.is_authenticated
        except (RuntimeError, AttributeError, RecursionError):
            pass  # Ignore recursion errors
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"PROCESS_ORDERS","location":"order_processing.py:6","message":"process_orders function entry","data":{"user_authenticated":is_authenticated,"user_id_provided":bool(user_id)},"timestamp":int(time.time()*1000)})+'\n')
    except: pass
    # #endregion
    try:
        # Get user_id - either from parameter or safely from current_user
        if user_id is None:
            try:
                if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
                    return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication required</div><div style='margin-bottom: 12px;'>Please log in to access this feature.</div><a href='/login' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Log In →</a></div></div>"}
                # Store user_id immediately to prevent recursion
                user_id = getattr(current_user, 'id', None)
            except (RuntimeError, AttributeError, RecursionError) as e:
                return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication error</div><div style='margin-bottom: 12px;'>Please refresh the page and try again.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
        
        if not user_id:
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication required</div><div style='margin-bottom: 12px;'>Please log in to access this feature.</div><a href='/login' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Log In →</a></div></div>"}
        
        # #region agent log
        try:
            import json
            import time
            with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"PROCESS_ORDERS","location":"order_processing.py:11","message":"Before database query","data":{"user_id":user_id},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
        # #region agent log
        try:
            import json
            import time
            with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"PROCESS_ORDERS","location":"order_processing.py:11","message":"After database query","data":{"store_found":bool(store),"has_shop_url":bool(store and store.shop_url) if store else False},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        
        if not store:
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>No Shopify store connected</div><div style='margin-bottom: 12px;'>Connect your store to view and manage orders.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Connect Store →</a></div></div>"}
        
        client = ShopifyClient(store.shop_url, store.access_token)
        
        # Get ONLY unfulfilled/pending orders that need action
        # Filter for: financial_status=pending OR fulfillment_status=unfulfilled
        try:
            # Fetch orders with pending payment status
            pending_orders_data = client._make_request("orders.json?financial_status=pending&limit=250")
            # Fetch orders that are paid but unfulfilled
            unfulfilled_orders_data = client._make_request("orders.json?financial_status=paid&fulfillment_status=unfulfilled&limit=250")
        except requests.exceptions.Timeout:
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Connection timeout</div><div style='margin-bottom: 12px;'>Shopify API is taking too long to respond. Please try again in a moment.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Connection error</div><div style='margin-bottom: 12px;'>Cannot connect to Shopify. Check your internet connection and verify your store is connected.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
        except Exception as e:
            return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Shopify API error</div><div style='margin-bottom: 12px;'>{str(e)}</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
        
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
            return {"success": True, "message": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 8px 12px; background: #f0fdf4; border-left: 2px solid #16a34a; border-radius: 4px; font-size: 12px; color: #166534;'>✅ No pending orders</div>"}
        
        # Build minimalistic HTML output with unified style (same as inventory/reports)
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        
        # Unified minimalistic style
        html = f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'>"
        html += f"<div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Pending Orders ({len(all_orders)})</div>"
        
        # Summary box - minimalistic
        html += f"<div style='padding: 8px 12px; background: #fffbeb; border-left: 2px solid #f59e0b; border-radius: 4px; margin-bottom: 12px; font-size: 11px; color: #92400e;'>Requires action</div>"
        
        # Show orders - minimalistic, same style as inventory/reports
        for order in all_orders[:50]:  # Show up to 50 orders
            order_name = order.get('name', 'N/A')
            total = order.get('total_price', '0')
            financial_status = order.get('financial_status', 'pending')
            fulfillment_status = order.get('fulfillment_status', 'unfulfilled')
            
            # Determine status and color
            if financial_status == 'pending':
                status_text = "Pending"
                border_color = '#f59e0b'
            elif fulfillment_status == 'unfulfilled':
                status_text = "Unfulfilled"
                border_color = '#dc2626'
            else:
                status_text = "Action needed"
                border_color = '#f59e0b'
            
            html += f"""
            <div style='padding: 10px 12px; margin: 6px 0; background: #fff; border-left: 2px solid {border_color}; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;'>
                <div style='flex: 1;'>
                    <div style='font-weight: 500; color: #171717; font-size: 13px;'>{order_name}</div>
                    <div style='color: #737373; margin-top: 2px; font-size: 11px;'>{status_text}</div>
                </div>
                <div style='text-align: right; margin-left: 16px;'>
                    <div style='font-weight: 600; color: #171717; font-size: 13px;'>${total}</div>
                </div>
            </div>
            """
        
        html += f"<div style='color: #a3a3a3; font-size: 10px; margin-top: 12px; text-align: right;'>Updated: {timestamp}</div>"
        html += "</div>"
        
        # #region agent log
        try:
            import json
            import time
            with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"PROCESS_ORDERS","location":"order_processing.py:95","message":"process_orders returning success","data":{"html_length":len(html)},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        
        return {"success": True, "message": html}
        
    except Exception as e:
        # #region agent log
        try:
            import json
            import time
            with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"PROCESS_ORDERS","location":"order_processing.py:98","message":"process_orders exception","data":{"error":str(e)[:200]},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Unexpected error</div><div style='margin-bottom: 12px;'>{str(e)}</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
