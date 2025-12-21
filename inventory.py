from flask_login import current_user
from models import ShopifyStore
from shopify_integration import ShopifyClient
import requests

def check_inventory():
    """Check inventory levels and return low stock alerts"""
    # Check if current_user is available and authenticated
    try:
        if not current_user or not hasattr(current_user, 'id') or not current_user.is_authenticated:
            return {"success": False, "error": "<div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication required</div><div style='margin-bottom: 12px;'>Please log in to access this feature.</div><a href='/login' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Log In →</a></div>"}
    except Exception:
        return {"success": False, "error": "<div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication required</div><div style='margin-bottom: 12px;'>Please log in to access this feature.</div><a href='/login' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Log In →</a></div>"}
    
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    
    if not store:
        return {"success": False, "error": "<div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>No Shopify store connected</div><div style='margin-bottom: 12px;'>Connect your store to check inventory levels and get low-stock alerts.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Connect Store →</a></div>"}
    
    try:
        client = ShopifyClient(store.shop_url, store.access_token)
        
        # Get products with error handling
        try:
            products = client.get_products()
        except requests.exceptions.Timeout:
            return {"success": False, "error": "<div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Connection timeout</div><div style='margin-bottom: 12px;'>Shopify API is taking too long to respond. Please try again in a moment.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div>"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "<div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Connection error</div><div style='margin-bottom: 12px;'>Cannot connect to Shopify. Check your internet connection and verify your store is connected.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div>"}
        except Exception as e:
            return {"success": False, "error": f"<div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Shopify API error</div><div style='margin-bottom: 12px;'>{str(e)}</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div>"}
        
        # Check if products returned an error
        if isinstance(products, dict) and "error" in products:
            return {"success": False, "error": f"Shopify returned an error: {products['error']}"}
        
        if not products or len(products) == 0:
            return {"success": True, "message": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 8px 12px; background: #f0fdf4; border-left: 2px solid #16a34a; border-radius: 4px; font-size: 12px; color: #166534;'>✅ No products found in your store.</div>"}
        
        # Sort products by stock level (lowest first = highest priority)
        sorted_products = sorted(products, key=lambda x: x.get('stock', 0))
        
        threshold = 10
        low_stock_count = sum(1 for p in products if p.get('stock', 0) < threshold)
        
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
        
        return {"success": True, "message": message}
    
    except Exception as e:
        return {"success": False, "error": f"<div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Unexpected error</div><div style='margin-bottom: 12px;'>{str(e)}</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div>"}

def update_inventory():
    """Update inventory - wrapper for check_inventory"""
    try:
        # Try to use Flask application context if available
        from flask import has_app_context, current_app
        if has_app_context():
            return check_inventory()
        else:
            # If no app context, return a helpful error message
            return {"success": False, "error": "This function requires a Flask application context. Please call it from within a Flask route or with app.app_context()."}
    except ImportError:
        # If Flask is not available, try without context (will fail gracefully)
        try:
            return check_inventory()
        except Exception as e:
            return {"success": False, "error": f"Function requires Flask application context: {str(e)}"}
