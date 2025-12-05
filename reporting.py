from shopify_integration import ShopifyClient
from flask_login import current_user
from models import ShopifyStore
from logging_config import logger

def generate_report():
    """Generate revenue report from Shopify data"""
    try:
        if not current_user.is_authenticated:
            return {"success": False, "error": "Not authenticated"}
        
        store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
        
        if not store:
            return {"success": False, "error": "No Shopify store connected. Go to Settings."}
        
        client = ShopifyClient(store.shop_url, store.access_token)
        
        # Fetch ALL paid orders using proper Shopify pagination
        # Shopify REST API uses cursor-based pagination via Link headers
        all_orders = []
        limit = 250  # Shopify max per page
        endpoint = f"orders.json?financial_status=paid&limit={limit}"
        max_iterations = 50  # Safety limit: ~12,500 orders
        
        try:
            for iteration in range(max_iterations):
                # Make request and get response
                orders_data = client._make_request(endpoint)
                
                if "error" in orders_data:
                    # If error on first request, return error
                    if iteration == 0:
                        return {"success": False, "error": f"Shopify error: {orders_data['error']}"}
                    # Otherwise, we've fetched all available orders
                    break
                
                orders = orders_data.get('orders', [])
                if not orders or len(orders) == 0:
                    break
                
                all_orders.extend(orders)
                
                # Check if we got fewer than limit (last page)
                if len(orders) < limit:
                    break
                
                # For Shopify REST API, we need to use the Link header or since_id for pagination
                # Since _make_request only returns JSON, we'll use since_id pagination
                # Get the highest order ID from current batch
                if orders:
                    last_order_id = max(order.get('id', 0) for order in orders)
                    endpoint = f"orders.json?financial_status=paid&limit={limit}&since_id={last_order_id}"
                else:
                    break
                    
        except Exception as e:
            # If pagination fails, try fetching without pagination (all orders, may be limited)
            try:
                orders_data = client._make_request("orders.json?financial_status=paid&limit=250")
                if "error" not in orders_data:
                    all_orders = orders_data.get('orders', [])
                    logger.warning(f"Pagination failed, fetched {len(all_orders)} orders without pagination")
            except Exception:
                return {"success": False, "error": f"Shopify API error: {str(e)}"}
        
        if len(all_orders) == 0:
            return {"success": True, "message": "<div style='padding: 16px; background: #fffbeb; border-radius: 6px; border-left: 3px solid #f59e0b; color: #92400e; font-size: 14px;'>No paid orders found.</div>"}
        
        # Calculate ALL-TIME revenue by product from ALL orders
        product_revenue = {}
        total_revenue = 0
        total_orders = len(all_orders)
        
        for order in all_orders:
            for item in order.get('line_items', []):
                product_name = item.get('title', 'Unknown')
                price = float(item.get('price', 0))
                quantity = item.get('quantity', 1)
                revenue = price * quantity
                
                if product_name in product_revenue:
                    product_revenue[product_name] += revenue
                else:
                    product_revenue[product_name] = revenue
                
                total_revenue += revenue
        
        # Sort by revenue
        sorted_products = sorted(product_revenue.items(), key=lambda x: x[1], reverse=True)
        
        # Build HTML report
        html = f"<div style='margin: 16px 0;'><h4 style='font-size: 15px; font-weight: 600; color: #171717; margin-bottom: 12px;'>All-Time Revenue Report (Top Products)</h4>"
        html += f"<div style='padding: 12px; background: #f0fdf4; border-radius: 6px; border-left: 3px solid #16a34a; margin-bottom: 16px;'>"
        html += f"<div style='font-weight: 600; color: #166534; font-size: 14px;'>Total Revenue: ${total_revenue:,.2f}</div>"
        html += f"<div style='color: #166534; font-size: 13px; margin-top: 4px;'>From {total_orders} paid orders (all-time data)</div>"
        html += "</div>"
        
        for product, revenue in sorted_products[:10]:
            percentage = (revenue / total_revenue) * 100 if total_revenue > 0 else 0
            html += f"""
            <div style='padding: 12px; margin: 8px 0; background: #fafafa; border-radius: 6px; border-left: 3px solid #16a34a;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div style='font-weight: 500; color: #171717; font-size: 14px;'>{product}</div>
                    <div style='font-weight: 600; color: #16a34a; font-size: 14px;'>${revenue:,.2f}</div>
                </div>
                <div style='color: #737373; font-size: 13px; margin-top: 4px;'>{percentage:.1f}% of total revenue</div>
            </div>
            """
        
        html += "</div>"
        
        return {"success": True, "message": html}
        
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
