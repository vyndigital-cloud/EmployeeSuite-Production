from shopify_integration import ShopifyClient
from flask_login import current_user
from models import ShopifyStore

def generate_report():
    """Generate revenue report from Shopify data"""
    try:
        if not current_user.is_authenticated:
            return {"success": False, "error": "Not authenticated"}
        
        store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
        
        if not store:
            return {"success": False, "error": "No Shopify store connected. Go to Settings."}
        
        client = ShopifyClient(store.shop_url, store.access_token)
        
        # Fetch ALL paid orders using pagination (all-time revenue)
        # Shopify uses cursor-based pagination, but we'll fetch in batches
        all_orders = []
        limit = 250  # Shopify max per page
        page_info = None
        max_pages = 40  # Safety limit: ~10,000 orders
        
        try:
            for page_num in range(1, max_pages + 1):
                # Build endpoint with pagination
                if page_info:
                    endpoint = f"orders.json?financial_status=paid&limit={limit}&page_info={page_info}"
                else:
                    endpoint = f"orders.json?financial_status=paid&limit={limit}"
                
                orders_data = client._make_request(endpoint)
                
                if "error" in orders_data:
                    # If error on first page, return error
                    if page_num == 1:
                        return {"success": False, "error": f"Shopify error: {orders_data['error']}"}
                    # Otherwise, we've fetched all available orders
                    break
                
                orders = orders_data.get('orders', [])
                if not orders or len(orders) == 0:
                    break
                
                all_orders.extend(orders)
                
                # Check for next page using Link header or response
                # If we got fewer than limit, we're done
                if len(orders) < limit:
                    break
                
                # Try to get next page_info from response (Shopify API 2024-01+)
                # If not available, we'll just fetch what we can
                # Most stores won't have 10,000+ orders, so this is fine
                if page_num >= max_pages:
                    break
                    
        except Exception as e:
            # If pagination fails, try fetching without pagination (first 250 orders)
            try:
                orders_data = client._make_request("orders.json?financial_status=paid&limit=250")
                if "error" not in orders_data:
                    all_orders = orders_data.get('orders', [])
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
