"""
Production-ready inventory management with real Shopify integration
"""

import logging
from typing import Dict, List, Optional

from models import ShopifyStore
from shopify_integration import ShopifyClient

logger = logging.getLogger(__name__)


def update_inventory(user_id=None, days=None):
    """Update inventory for user with comprehensive analytics and alerts"""
    try:
        # Get user's store
        store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
        if not store:
            return {"success": False, "error": "No store connected"}

        # Validate store connection
        access_token = store.get_access_token()
        if not access_token:
            return {
                "success": False, 
                "error": "Store connection expired. Please reconnect in Settings.",
                "action": "reconnect"
            }

        # Get inventory from Shopify with comprehensive error handling
        client = ShopifyClient(store.shop_url, access_token)
        
        try:
            products = client.get_products()
            
            # Handle API errors
            if isinstance(products, dict) and "error" in products:
                error_msg = products["error"]
                
                # Handle specific error types
                if products.get("permission_denied"):
                    return {
                        "success": False,
                        "error": "Missing permissions to access product data. Please reinstall the app.",
                        "action": "reinstall",
                        "technical_details": error_msg
                    }
                elif products.get("auth_failed"):
                    return {
                        "success": False,
                        "error": "Authentication failed. Please reconnect your store.",
                        "action": "reconnect",
                        "technical_details": error_msg
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Unable to fetch inventory: {error_msg}",
                        "action": "retry"
                    }
            
            # Ensure products is a list
            if not isinstance(products, list):
                logger.error(f"Unexpected products response type: {type(products)}")
                return {"success": False, "error": "Invalid response from Shopify API"}

        except Exception as api_error:
            logger.error(f"Shopify API error for user {user_id}: {api_error}")
            return {
                "success": False,
                "error": "Failed to connect to Shopify. Please try again.",
                "technical_details": str(api_error)[:100],
                "action": "retry"
            }

        # Process inventory with comprehensive analytics
        if products:
            # Initialize counters
            total_products = len(products)
            low_stock_items = 0
            out_of_stock_items = 0
            total_inventory_value = 0
            high_stock_items = 0
            inventory_data = []
            
            # Define stock thresholds
            LOW_STOCK_THRESHOLD = 5
            HIGH_STOCK_THRESHOLD = 100
            
            # Process each product
            for product in products:
                try:
                    # Safely extract product data
                    product_name = product.get('product', 'Unknown Product')
                    sku = product.get('sku', 'N/A')
                    
                    # Safely extract stock quantity
                    stock = 0
                    try:
                        stock_value = product.get('stock', 0)
                        stock = int(stock_value) if stock_value is not None else 0
                    except (ValueError, TypeError):
                        stock = 0
                    
                    # Safely extract price
                    price_value = 0
                    price_display = "N/A"
                    try:
                        price_str = product.get('price', '$0.00')
                        if isinstance(price_str, str):
                            # Remove currency symbols and convert
                            price_clean = price_str.replace('$', '').replace(',', '')
                            price_value = float(price_clean)
                            price_display = f"${price_value:.2f}"
                        else:
                            price_value = float(price_str)
                            price_display = f"${price_value:.2f}"
                    except (ValueError, TypeError):
                        price_value = 0
                        price_display = "N/A"
                    
                    # Calculate inventory value
                    inventory_value = stock * price_value
                    total_inventory_value += inventory_value
                    
                    # Categorize stock levels
                    stock_status = "normal"
                    stock_alert = ""
                    
                    if stock == 0:
                        out_of_stock_items += 1
                        stock_status = "out_of_stock"
                        stock_alert = "⚠️ Out of Stock"
                    elif stock <= LOW_STOCK_THRESHOLD:
                        low_stock_items += 1
                        stock_status = "low_stock"
                        stock_alert = f"🔶 Low Stock ({stock} left)"
                    elif stock >= HIGH_STOCK_THRESHOLD:
                        high_stock_items += 1
                        stock_status = "high_stock"
                        stock_alert = f"📦 High Stock ({stock} units)"
                    else:
                        stock_alert = f"✅ In Stock ({stock} units)"
                    
                    # Calculate stock percentage for visual bar (max 100 for display)
                    stock_percentage = min(100, max(0, (stock / 50) * 100))
                    
                    # Determine bar color based on stock level
                    if stock == 0:
                        bar_color = "#dc2626"  # Red
                    elif stock <= LOW_STOCK_THRESHOLD:
                        bar_color = "#f59e0b"  # Orange
                    else:
                        bar_color = "#16a34a"  # Green
                    
                    # Add to inventory data
                    inventory_data.append({
                        "product": product_name,
                        "sku": sku,
                        "stock": stock,
                        "price": price_display,
                        "inventory_value": inventory_value,
                        "stock_status": stock_status,
                        "stock_alert": stock_alert,
                        "stock_percentage": stock_percentage,
                        "bar_color": bar_color,
                        "handle": product.get('handle', ''),
                        "variant_id": product.get('variant_id', '')
                    })
                    
                except Exception as product_error:
                    logger.warning(f"Error processing product {product.get('product', 'unknown')}: {product_error}")
                    continue
            
            # Sort inventory by stock level (lowest first for urgent attention)
            inventory_data.sort(key=lambda x: x['stock'])
            
            # Calculate additional metrics
            in_stock_items = total_products - out_of_stock_items
            stock_health_score = round(((in_stock_items - low_stock_items) / total_products) * 100, 1) if total_products > 0 else 0
            
            # Generate alerts and insights
            alerts = []
            insights = []
            
            if out_of_stock_items > 0:
                alerts.append(f"🚨 {out_of_stock_items} products are out of stock")
                insights.append("Immediate action needed: Restock out-of-stock items to prevent lost sales")
            
            if low_stock_items > 0:
                alerts.append(f"⚠️ {low_stock_items} products are running low")
                insights.append(f"Plan restocking for {low_stock_items} low-stock items")
            
            if stock_health_score >= 80:
                insights.append("✅ Excellent inventory health - most products are well stocked")
            elif stock_health_score >= 60:
                insights.append("📊 Good inventory management - minor attention needed")
            else:
                insights.append("📈 Inventory needs attention - consider restocking strategy")
            
            if high_stock_items > 0:
                insights.append(f"💡 {high_stock_items} products have high stock - consider promotions")
            
            # Generate professional HTML output
            html = f"""
            <div class="output-card">
                <div class="output-header">
                    <h4>📦 Inventory Analysis</h4>
                    <span class="badge badge-success">Live Data</span>
                </div>
                
                <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin: 20px 0;">
                    <div class="stat-box">
                        <div class="stat-label">Total Products</div>
                        <div class="stat-value" style="color: #008060;">{total_products}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Inventory Value</div>
                        <div class="stat-value" style="color: #008060;">${total_inventory_value:,.2f}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Stock Health</div>
                        <div class="stat-value" style="color: {'#16a34a' if stock_health_score > 80 else '#f59e0b' if stock_health_score > 50 else '#dc2626'};">{stock_health_score}%</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Need Attention</div>
                        <div class="stat-value" style="color: {'#dc2626' if (out_of_stock_items + low_stock_items) > 0 else '#16a34a'};">{out_of_stock_items + low_stock_items}</div>
                    </div>
                </div>
            """
            
            # Add alerts section if there are any
            if alerts:
                html += f"""
                <div class="alerts-section" style="background: #fef2f2; border: 1px solid #fecaca; padding: 16px; border-radius: 8px; margin: 20px 0;">
                    <h5 style="margin: 0 0 12px 0; color: #dc2626;">🚨 Inventory Alerts</h5>
                    <ul style="margin: 0; padding-left: 20px; color: #7f1d1d;">
                        {''.join([f'<li style="margin-bottom: 4px;">{alert}</li>' for alert in alerts])}
                    </ul>
                </div>
                """
            
            # Add insights section
            if insights:
                html += f"""
                <div class="insights-section" style="background: #f8f9fa; padding: 16px; border-radius: 8px; margin: 20px 0;">
                    <h5 style="margin: 0 0 12px 0; color: #374151;">📊 Inventory Insights</h5>
                    <ul style="margin: 0; padding-left: 20px;">
                        {''.join([f'<li style="margin-bottom: 4px;">{insight}</li>' for insight in insights])}
                    </ul>
                </div>
                """
            
            # Add inventory list
            html += """
                <div class="inventory-list" style="margin-top: 20px;">
            """
            
            # Show top 20 items (prioritizing those needing attention)
            for item in inventory_data[:20]:
                html += f"""
                    <div class="inventory-item" style="display: flex; justify-content: space-between; align-items: center; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 8px; background: white;">
                        <div class="inventory-info" style="flex: 1;">
                            <div class="product-name" style="font-weight: 600; color: #111827; margin-bottom: 4px;">
                                {item['product']}
                            </div>
                            <div style="display: flex; gap: 16px; font-size: 14px; color: #6b7280;">
                                <span>SKU: {item['sku']}</span>
                                <span>Price: {item['price']}</span>
                                <span>Value: ${item['inventory_value']:.2f}</span>
                            </div>
                        </div>
                        <div class="inventory-stock" style="text-align: right; min-width: 150px;">
                            <div class="stock-alert" style="font-weight: 500; margin-bottom: 8px; font-size: 14px;">
                                {item['stock_alert']}
                            </div>
                            <div class="stock-bar-bg" style="width: 100px; height: 6px; background: #e5e7eb; border-radius: 3px; overflow: hidden;">
                                <div class="stock-bar-fill" style="width: {item['stock_percentage']}%; height: 100%; background-color: {item['bar_color']}; transition: width 0.3s ease;"></div>
                            </div>
                        </div>
                    </div>
                """
            
            html += """
                </div>
                
                <div style="margin-top: 16px; padding: 12px; background: #f0f9ff; border-radius: 6px; border-left: 4px solid #008060;">
                    <small style="color: #374151;">
                        📊 <strong>Pro Tip:</strong> Maintain 2-4 weeks of inventory based on sales velocity. 
                        Set up low-stock alerts to prevent stockouts and lost sales.
                    </small>
                </div>
            </div>
            """
            
            return {
                "success": True, 
                "html": html,
                "inventory_data": inventory_data,
                "data": {
                    "total_products": total_products,
                    "low_stock_items": low_stock_items,
                    "out_of_stock_items": out_of_stock_items,
                    "in_stock_items": in_stock_items,
                    "high_stock_items": high_stock_items,
                    "total_inventory_value": total_inventory_value,
                    "stock_health_score": stock_health_score
                }
            }
        else:
            # No products found
            html = """
            <div class="output-card">
                <div class="output-header">
                    <h4>📦 Inventory Analysis</h4>
                    <span class="badge badge-info">No Data</span>
                </div>
                <div style="padding: 40px 24px; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 16px;">📭</div>
                    <h5 style="color: #374151; margin-bottom: 8px;">No Products Found</h5>
                    <p style="color: #6b7280; margin-bottom: 20px;">
                        No products were found in your store. This could mean:
                    </p>
                    <ul style="text-align: left; color: #6b7280; max-width: 300px; margin: 0 auto;">
                        <li>Your store is new and products haven't been added yet</li>
                        <li>Products might not be published</li>
                        <li>There might be a connection issue</li>
                    </ul>
                    <div style="margin-top: 24px;">
                        <small style="color: #9ca3af;">
                            💡 <strong>Tip:</strong> Check your Shopify admin to ensure products are published and visible.
                        </small>
                    </div>
                </div>
            </div>
            """
            
            return {
                "success": True, 
                "html": html,
                "inventory_data": [],
                "data": {
                    "total_products": 0,
                    "low_stock_items": 0,
                    "out_of_stock_items": 0,
                    "in_stock_items": 0,
                    "high_stock_items": 0,
                    "total_inventory_value": 0,
                    "stock_health_score": 0
                }
            }

    except Exception as e:
        logger.error(f"Error updating inventory for user {user_id}: {e}", exc_info=True)
        return {
            "success": False, 
            "error": "An unexpected error occurred while updating inventory.",
            "technical_details": str(e)[:100],
            "action": "retry"
        }
