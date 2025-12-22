from shopify_integration import ShopifyClient
from flask_login import current_user
from models import ShopifyStore, db
from logging_config import logger

def generate_report(user_id=None):
    """Generate revenue report from Shopify data"""
    try:
        # Get user_id - either passed as parameter or from current_user
        # This prevents recursion issues
        if user_id is None:
            if not current_user.is_authenticated:
                return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication required</div><div style='margin-bottom: 12px;'>Please log in to access this feature.</div><a href='/login' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Log In →</a></div></div>"}
            # Store user_id before accessing to avoid recursion
            user_id = current_user.id if hasattr(current_user, 'id') else getattr(current_user, 'id', None)
        
        store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
        
        if not store:
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>No Shopify store connected</div><div style='margin-bottom: 12px;'>Connect your store to generate revenue reports and analytics.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Connect Store →</a></div></div>"}
        
        client = ShopifyClient(store.shop_url, store.access_token)
        
        # Fetch ALL orders first, then filter client-side to ensure we get everything
        # This avoids pagination issues with since_id that might skip orders
        # IMPORTANT: Use status=any to get ALL orders (including archived/closed)
        all_orders_raw = []
        limit = 250  # Shopify max per page
        endpoint = f"orders.json?status=any&limit={limit}"  # Fetch ALL orders (any status), filter client-side
        max_iterations = 20  # Reduced for faster performance: ~5,000 orders (enough for most stores)
        
        try:
            for iteration in range(max_iterations):
                # Make request and get response
                orders_data = client._make_request(endpoint)
                
                if "error" in orders_data:
                    # If error on first request, check if it's authentication failure
                    if iteration == 0:
                        error_msg = orders_data['error']
                        # If authentication failed, mark store as inactive
                        if "Authentication failed" in error_msg or "401" in str(orders_data):
                            logger.warning(f"Authentication failed for store {store.shop_url} (user {user_id}) - marking as inactive")
                            try:
                                store.is_active = False
                                db.session.commit()
                            except Exception as db_error:
                                logger.error(f"Failed to update store status: {db_error}")
                                db.session.rollback()
                            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Shopify error</div><div style='margin-bottom: 12px;'>Authentication failed - Please reconnect your store</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
                        return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Shopify error</div><div style='margin-bottom: 12px;'>{orders_data['error']}</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
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
                return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Shopify API error</div><div style='margin-bottom: 12px;'>{str(e)}</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
        
        # Filter for paid orders client-side to ensure we get ALL paid orders
        # Debug: Log all financial_status values to see what we're getting
        financial_statuses = [order.get('financial_status', 'MISSING') for order in all_orders_raw]
        logger.info(f"Financial statuses found: {set(financial_statuses)}")
        logger.info(f"Total orders fetched: {len(all_orders_raw)}")
        
        # Limit processing to prevent memory issues (max 10,000 orders)
        MAX_ORDERS_TO_PROCESS = 10000
        if len(all_orders_raw) > MAX_ORDERS_TO_PROCESS:
            logger.warning(f"Large dataset detected ({len(all_orders_raw)} orders). Processing first {MAX_ORDERS_TO_PROCESS} orders to prevent memory issues.")
            all_orders_raw = all_orders_raw[:MAX_ORDERS_TO_PROCESS]
        
        all_orders = [order for order in all_orders_raw if order.get('financial_status', '').lower() == 'paid']
        logger.info(f"Filtered to {len(all_orders)} paid orders from {len(all_orders_raw)} total orders")
        
        # Additional debug: Show order IDs and totals
        if all_orders:
            order_totals = [float(order.get('total_price', 0)) for order in all_orders]
            logger.info(f"Paid order totals: {order_totals}")
            logger.info(f"Sum of paid orders: ${sum(order_totals):,.2f}")
        
        if len(all_orders) == 0:
            return {"success": True, "message": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 8px 12px; background: #f0fdf4; border-left: 2px solid #16a34a; border-radius: 4px; font-size: 12px; color: #166534;'>✅ No paid orders found.</div>"}
        
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
        
        # Build minimalistic HTML report with unified style (same as inventory)
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        
        # Unified minimalistic style (matches inventory)
        html = f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'>"
        # Title row with export button in top right - aligned with title
        html += f"<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; width: 100%;'>"
        html += f"<div style='font-size: 13px; font-weight: 600; color: #171717; flex: 1;'>Revenue Report (Top {min(10, len(sorted_products))} Products)</div>"
        html += f"<a href='/api/export/report' style='padding: 6px 12px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 500; white-space: nowrap; transition: background 0.15s; margin-left: 16px; flex-shrink: 0;'>📥 Export CSV</a>"
        html += f"</div>"
        
        # Summary box - minimalistic (NO button here)
        html += f"<div style='padding: 8px 12px; background: #f0fdf4; border-left: 2px solid #16a34a; border-radius: 4px; margin-bottom: 12px;'>"
        html += f"<div style='font-weight: 600; color: #166534; font-size: 12px;'>${total_revenue:,.2f}</div>"
        html += f"<div style='color: #166534; font-size: 11px; margin-top: 2px;'>{total_orders} orders</div>"
        html += "</div>"
        
        # Product list - minimalistic, same style as inventory
        for product, revenue in sorted_products[:10]:
            percentage = (revenue / total_revenue) * 100 if total_revenue > 0 else 0
            html += f"""
            <div style='padding: 10px 12px; margin: 6px 0; background: #fff; border-left: 2px solid #16a34a; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;'>
                <div style='flex: 1;'>
                    <div style='font-weight: 500; color: #171717; font-size: 13px;'>{product}</div>
                    <div style='color: #737373; margin-top: 2px; font-size: 11px;'>{percentage:.1f}% of total</div>
                </div>
                <div style='text-align: right; margin-left: 16px;'>
                    <div style='font-weight: 600; color: #16a34a; font-size: 13px;'>${revenue:,.2f}</div>
                </div>
            </div>
            """
        
        html += f"<div style='color: #a3a3a3; font-size: 10px; margin-top: 12px; text-align: right;'>Updated: {timestamp}</div>"
        html += "</div>"
        
        # Store report data for CSV export
        report_data = {
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'products': sorted_products
        }
        
        return {"success": True, "message": html, "report_data": report_data}
        
    except Exception as e:
        return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Unexpected error</div><div style='margin-bottom: 12px;'>{str(e)}</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
