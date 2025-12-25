from flask_login import current_user
from models import ShopifyStore, db
from shopify_integration import ShopifyClient
from logging_config import logger
import requests

def check_inventory(user_id=None):
    """Check inventory levels and return low stock alerts"""
    # #region agent log
    try:
        import json
        import time
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL_BROKEN","location":"inventory.py:7","message":"check_inventory ENTRY","data":{"user_id_provided":bool(user_id),"user_id":user_id},"timestamp":int(time.time()*1000)})+'\n')
    except: pass
    # #endregion
    # CRITICAL: Accept user_id as parameter to prevent recursion from accessing current_user
    # Get user_id - either from parameter or safely from current_user
    if user_id is None:
        try:
            if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
                return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading inventory</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication required</div><div style='margin-bottom: 12px;'>Please log in to access this feature.</div><a href='/login' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Log In →</a></div></div>"}
            # Store user_id immediately to prevent recursion
            user_id = getattr(current_user, 'id', None)
        except (RuntimeError, AttributeError, RecursionError) as e:
            return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading inventory</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication error</div><div style='margin-bottom: 12px;'>Please refresh the page and try again.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
    
    if not user_id:
        return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading inventory</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication required</div><div style='margin-bottom: 12px;'>Please log in to access this feature.</div><a href='/login' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Log In →</a></div></div>"}
    
    # #region agent log
    try:
        import json
        import time
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL_BROKEN","location":"inventory.py:23","message":"Before database query","data":{"user_id":user_id},"timestamp":int(time.time()*1000)})+'\n')
    except: pass
    # #endregion
    store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
    # #region agent log
    try:
        import json
        import time
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL_BROKEN","location":"inventory.py:25","message":"After database query","data":{"store_found":bool(store),"has_shop_url":bool(store and store.shop_url) if store else False},"timestamp":int(time.time()*1000)})+'\n')
    except: pass
    # #endregion
    
    if not store:
        return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading inventory</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>No Shopify store connected</div><div style='margin-bottom: 12px;'>Connect your store to check inventory levels and get low-stock alerts.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Connect Store →</a></div></div>"}
    
    try:
        client = ShopifyClient(store.shop_url, store.access_token)
        # #region agent log
        try:
            import json
            import time
            with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL_BROKEN","location":"inventory.py:29","message":"Before get_products call","data":{"shop_url":store.shop_url[:50] if store else ""},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        
        # Get products with error handling
        try:
            products = client.get_products()
            # #region agent log
            try:
                import json
                import time
                with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL_BROKEN","location":"inventory.py:34","message":"After get_products call","data":{"is_dict":isinstance(products,dict),"has_error":isinstance(products,dict) and 'error' in products,"is_list":isinstance(products,list),"products_count":len(products) if isinstance(products,list) else 0},"timestamp":int(time.time()*1000)})+'\n')
            except: pass
            # #endregion
        except requests.exceptions.Timeout:
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading inventory</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Connection timeout</div><div style='margin-bottom: 12px;'>Shopify API is taking too long to respond. Please try again in a moment.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading inventory</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Connection error</div><div style='margin-bottom: 12px;'>Cannot connect to Shopify. Check your internet connection and verify your store is connected.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
        except Exception as e:
            return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading inventory</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Shopify API error</div><div style='margin-bottom: 12px;'>{str(e)}</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
        
        # Check if products returned an error
        if isinstance(products, dict) and "error" in products:
            error_msg = products['error']
            # If authentication failed, mark store as inactive
            if "Authentication failed" in error_msg or "401" in str(products):
                logger.warning(f"Authentication failed for store {store.shop_url} (user {user_id}) - marking as inactive")
                try:
                    store.is_active = False
                    db.session.commit()
                except Exception as db_error:
                    logger.error(f"Failed to update store status: {db_error}")
                    db.session.rollback()
                return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading inventory</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Shopify error</div><div style='margin-bottom: 12px;'>Authentication failed - Please reconnect your store</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
            return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading inventory</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Shopify error</div><div style='margin-bottom: 12px;'>{error_msg}</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
        
        if not products or len(products) == 0:
            return {"success": True, "message": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 8px 12px; background: #f0fdf4; border-left: 2px solid #16a34a; border-radius: 4px; font-size: 12px; color: #166534;'>✅ No products found in your store.</div>"}
        
        # Sort products by stock level (lowest first = highest priority)
        sorted_products = sorted(products, key=lambda x: x.get('stock', 0))
        
        threshold = 10
        low_stock_count = sum(1 for p in products if p.get('stock', 0) < threshold)
        
        # Store inventory data in session for CSV export
        try:
            from flask import session
            session['inventory_data'] = products
        except Exception:
            pass  # Session might not be available, continue anyway
        
        # Build minimalistic inventory report with unified style
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        
        # Unified minimalistic style
        message = f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'>"
        message += f"<div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Inventory ({len(products)} products)</div>"
        
        if low_stock_count > 0:
            message += f"<div style='padding: 8px 12px; background: #fef2f2; border-left: 2px solid #dc2626; border-radius: 4px; margin-bottom: 12px; font-size: 11px; color: #991b1b;'>{low_stock_count} below {threshold} units</div>"
        else:
            message += f"<div style='padding: 8px 12px; background: #f0fdf4; border-left: 2px solid #16a34a; border-radius: 4px; margin-bottom: 12px; font-size: 11px; color: #166534;'>All products in stock</div>"
        
        # Show all products - lowest stock first (highest priority)
        for product in sorted_products:
            inventory = product.get('stock', 0)
            product_name = product.get('product', 'Unknown Product')
            sku = product.get('sku', 'N/A')
            price = product.get('price', 'N/A')
            
            # Determine color based on stock level
            # Negative stock (oversold) = RED (critical)
            # 0 stock = RED (critical, out of stock)
            # 1-9 stock (below threshold) = ORANGE (warning, low stock)
            # 10+ stock = GREEN (good, in stock)
            if inventory < 0:
                # Negative stock = oversold, critical
                alert_color = '#dc2626'
                border_color = '#dc2626'
            elif inventory == 0:
                # Zero stock = out of stock, critical
                alert_color = '#dc2626'
                border_color = '#dc2626'
            elif inventory < threshold:
                # Low stock (1-9) = warning
                alert_color = '#f59e0b'
                border_color = '#f59e0b'
            else:
                # Good stock (10+) = healthy
                alert_color = '#16a34a'
                border_color = '#16a34a'
            
            # Minimalistic compact style - EXACT match to orders/revenue
            message += f"<div style='padding: 10px 12px; margin: 6px 0; background: #fff; border-left: 2px solid {border_color}; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;'><div style='flex: 1;'><div style='font-weight: 500; color: #171717; font-size: 13px;'>{product_name}</div><div style='color: #737373; margin-top: 2px; font-size: 11px;'>{sku} • {price}</div></div><div style='text-align: right; margin-left: 16px;'><div style='font-weight: 600; color: {alert_color}; font-size: 13px;'>{inventory}</div></div></div>"
        
        message += f"<div style='color: #a3a3a3; font-size: 10px; margin-top: 12px; text-align: right;'>Updated: {timestamp}</div>"
        message += "</div>"
        
        # Store inventory data in session for CSV export
        try:
            from flask import session
            session['inventory_data'] = products
        except Exception:
            pass  # Session might not be available, continue anyway
        
        return {"success": True, "message": message, "inventory_data": products}
    
    except Exception as e:
        return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading inventory</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Unexpected error</div><div style='margin-bottom: 12px;'>{str(e)}</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}

def update_inventory(user_id=None):
    """Update inventory - wrapper for check_inventory"""
    # CRITICAL: Accept user_id as parameter to prevent recursion
    try:
        # Try to use Flask application context if available
        from flask import has_app_context, current_app
        if has_app_context():
            return check_inventory(user_id=user_id)
        else:
            # If no app context, return a helpful error message
            return {"success": False, "error": "This function requires a Flask application context. Please call it from within a Flask route or with app.app_context()."}
    except ImportError:
        # If Flask is not available, try without context (will fail gracefully)
        try:
            return check_inventory(user_id=user_id)
        except Exception as e:
            return {"success": False, "error": f"Function requires Flask application context: {str(e)}"}
