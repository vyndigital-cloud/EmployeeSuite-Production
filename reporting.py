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
        
        # Fetch ALL orders first, then filter client-side to ensure we get everything
        # This avoids pagination issues with since_id that might skip orders
        # IMPORTANT: Use status=any to get ALL orders (including archived/closed)
        all_orders_raw = []
        limit = 250  # Shopify max per page
        endpoint = f"orders.json?status=any&limit={limit}"  # Fetch ALL orders (any status), filter client-side
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
                
                all_orders_raw.extend(orders)
                logger.info(f"Fetched {len(orders)} orders (iteration {iteration + 1}), total so far: {len(all_orders_raw)}")
                
                # Check if we got fewer than limit (last page)
                if len(orders) < limit:
                    logger.info(f"Fetched all orders. Total: {len(all_orders_raw)}")
                    break
                
                # For Shopify REST API, use since_id pagination
                # Get the highest order ID from current batch to fetch next page
                if orders:
                    last_order_id = max(order.get('id', 0) for order in orders)
                    endpoint = f"orders.json?status=any&limit={limit}&since_id={last_order_id}"
                else:
                    break
                    
        except Exception as e:
            # If pagination fails, try fetching without pagination (all orders, may be limited)
            try:
                orders_data = client._make_request("orders.json?status=any&limit=250")
                if "error" not in orders_data:
                    all_orders_raw = orders_data.get('orders', [])
                    logger.warning(f"Pagination failed, fetched {len(all_orders_raw)} orders without pagination")
            except Exception:
                return {"success": False, "error": f"Shopify API error: {str(e)}"}
        
        # Filter for paid orders client-side to ensure we get ALL paid orders
        all_orders = [order for order in all_orders_raw if order.get('financial_status', '').lower() == 'paid']
        logger.info(f"Filtered to {len(all_orders)} paid orders from {len(all_orders_raw)} total orders")
        
        if len(all_orders) == 0:
            return {"success": True, "message": "<div style='padding: 16px; background: #fffbeb; border-radius: 6px; border-left: 3px solid #f59e0b; color: #92400e; font-size: 14px;'>No paid orders found.</div>"}
        
        # Calculate ALL-TIME revenue by product from ALL orders
        # Use order['total_price'] to match Shopify API exactly (includes discounts, taxes, shipping)
        product_revenue = {}
        total_revenue = 0
        total_orders = len(all_orders)
        
        for order in all_orders:
            # Use order total_price to match Shopify API (same as test script)
            order_total = float(order.get('total_price', 0))
            total_revenue += order_total
            
            # Calculate product-level breakdown from line items
            # Note: Product breakdown uses line item prices (may not include order-level discounts)
            for item in order.get('line_items', []):
                product_name = item.get('title', 'Unknown')
                price = float(item.get('price', 0))
                quantity = item.get('quantity', 1)
                revenue = price * quantity
                
                if product_name in product_revenue:
                    product_revenue[product_name] += revenue
                else:
                    product_revenue[product_name] = revenue
        
        # Sort by revenue
        sorted_products = sorted(product_revenue.items(), key=lambda x: x[1], reverse=True)
        
        # Calculate additional metrics
        average_order_value = total_revenue / total_orders if total_orders > 0 else 0
        total_items = sum(sum(item.get('quantity', 1) for item in order.get('line_items', [])) for order in all_orders)
        average_items_per_order = total_items / total_orders if total_orders > 0 else 0
        
        # Build HTML report with real-time timestamp
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        html = f"<div style='margin: 16px 0;'><div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 12px;'><h4 style='font-size: 15px; font-weight: 600; color: #171717; margin: 0;'>All-Time Revenue Report (Top Products)</h4><button onclick='exportReport()' style='padding: 8px 16px; background: #4a7338; color: #fff; border: none; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.2s;'>📥 Export CSV</button></div>"
        html += f"<div style='padding: 16px; background: #f0fdf4; border-radius: 6px; border-left: 3px solid #16a34a; margin-bottom: 16px;'>"
        html += f"<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 12px;'>"
        html += f"<div><div style='font-size: 12px; color: #737373; margin-bottom: 4px;'>Total Revenue</div><div style='font-weight: 600; color: #166534; font-size: 18px;'>${total_revenue:,.2f}</div></div>"
        html += f"<div><div style='font-size: 12px; color: #737373; margin-bottom: 4px;'>Total Orders</div><div style='font-weight: 600; color: #166534; font-size: 18px;'>{total_orders}</div></div>"
        html += f"<div><div style='font-size: 12px; color: #737373; margin-bottom: 4px;'>Avg Order Value</div><div style='font-weight: 600; color: #166534; font-size: 18px;'>${average_order_value:,.2f}</div></div>"
        html += f"<div><div style='font-size: 12px; color: #737373; margin-bottom: 4px;'>Total Items Sold</div><div style='font-weight: 600; color: #166534; font-size: 18px;'>{int(total_items)}</div></div>"
        html += f"</div>"
        html += f"<div style='color: #737373; font-size: 12px; margin-top: 8px; font-style: italic; border-top: 1px solid #d1fae5; padding-top: 8px;'>🔄 Live data fetched: {timestamp}</div>"
        html += "</div>"
        
        # Store data for export (with enhanced metrics)
        html += f"<script>window.reportData = {{totalRevenue: {total_revenue}, totalOrders: {total_orders}, averageOrderValue: {average_order_value}, totalItems: {int(total_items)}, products: {sorted_products[:10]}, timestamp: '{timestamp}'}};</script>"
        
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
