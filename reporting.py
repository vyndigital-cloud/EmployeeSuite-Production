from shopify_integration import ShopifyClient
from flask_login import current_user
from models import ShopifyStore, db
from logging_config import logger

def generate_report(user_id=None, shop_url=None):
    """Generate revenue report from Shopify data"""
    # CRITICAL: Catch ALL exceptions including segfault precursors (BaseException)
    # This prevents worker crashes (code 139) from corrupting the entire process
    try:
        # Get user_id - either passed as parameter or from current_user
        # This prevents recursion issues
        if user_id is None:
            if not current_user.is_authenticated:
                return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication required</div><div style='margin-bottom: 12px;'>Please log in to access this feature.</div><a href='/login' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Log In →</a></div></div>"}
            # Store user_id before accessing to avoid recursion
            user_id = current_user.id if hasattr(current_user, 'id') else getattr(current_user, 'id', None)
        
        # CRITICAL: Fetch store with proper error handling to prevent segfaults
        # Segfaults happen when database connections are corrupted - we must catch ALL exceptions
        # DO NOT call db.session.remove() before query - let pool_pre_ping handle connection validation
        store = None
        try:
            # Let SQLAlchemy's pool_pre_ping validate the connection automatically
            # Removing sessions manually can corrupt connection state and cause segfaults
            # If shop_url is provided, use it to find the specific store; otherwise use first active store for user
            if shop_url:
                logger.info(f"Generating report for shop_url: {shop_url}, user_id: {user_id}")
                store = ShopifyStore.query.filter_by(shop_url=shop_url, is_active=True).first()
                # Verify the store belongs to this user (security check)
                if store and store.user_id != user_id:
                    logger.warning(f"Shop {shop_url} does not belong to user {user_id}, denying access")
                    store = None
            else:
                # Fallback: use first active store for user
                logger.info(f"No shop_url provided, using first active store for user_id: {user_id}")
                store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
        except BaseException as db_error:
            # Catch ALL exceptions including segfault precursors
            logger.error(f"Database error fetching store for user {user_id}: {type(db_error).__name__}: {str(db_error)}", exc_info=True)
            # CRITICAL: Only rollback on exception, DO NOT call db.session.remove() - it can cause segfaults
            # Let SQLAlchemy's pool_pre_ping handle connection validation automatically
            try:
                db.session.rollback()
            except Exception:
                pass  # Ignore rollback errors to prevent cascading failures
            # DO NOT call db.session.remove() here - it corrupts connection state and causes segfaults
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Database connection error</div><div style='margin-bottom: 12px;'>Please try again in a moment.</div></div></div>"}
        
        if not store:
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>No Shopify store connected</div><div style='margin-bottom: 12px;'>Connect your store to generate revenue reports and analytics.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Connect Store →</a></div></div>"}
        
        # Get decrypted access token
        access_token = store.get_access_token()
        if not access_token:
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Store not properly connected</div><div style='margin-bottom: 12px;'>Missing or invalid access token. Please reconnect your store.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Reconnect Store →</a></div></div>"}
        
        client = ShopifyClient(store.shop_url, access_token)
        
        # CRITICAL: Memory management - process in batches to prevent segfaults
        # Limit total memory usage by processing orders in chunks
        all_orders_raw = []
        limit = 250  # Shopify max per page
        endpoint = f"orders.json?status=any&limit={limit}"
        max_iterations = 20  # ~5,000 orders max to prevent memory issues
        
        # Memory-safe pagination with explicit cleanup
        # CRITICAL: DO NOT call db.session.remove() before queries - let pool_pre_ping handle validation
        # Removing sessions manually can corrupt connection state and cause segfaults
        try:
            for iteration in range(max_iterations):
                # Make request and get response
                orders_data = client._make_request(endpoint)
                
                if "error" in orders_data:
                    # If error on first request, check if it's authentication or permission failure
                    if iteration == 0:
                        error_msg = orders_data['error']
                        # Check for auth_failed flag from ShopifyClient (401)
                        if orders_data.get('auth_failed') or "Authentication failed" in error_msg or "401" in str(orders_data):
                            logger.warning(f"Authentication failed for store {store.shop_url} (user {user_id}) - marking as inactive")
                            # Mark store as inactive - user needs to reconnect
                            # CRITICAL: DO NOT call db.session.remove() before query - let pool_pre_ping handle validation
                            try:
                                store.is_active = False
                                db.session.commit()
                            except BaseException as db_error:
                                logger.error(f"Failed to update store status: {type(db_error).__name__}: {str(db_error)}", exc_info=True)
                                try:
                                    db.session.rollback()
                                except Exception:
                                    pass
                            finally:
                                # Session cleanup handled by teardown_appcontext
                                pass
                            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication failed</div><div style='margin-bottom: 12px;'>Your store connection has expired. Please reconnect your store to continue.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Reconnect Store →</a></div></div>"}
                        # Check for permission denied (403) - missing scopes
                        elif orders_data.get('permission_denied') or "Access denied" in error_msg or "403" in str(orders_data) or "permission" in error_msg.lower() or "Check your app permissions" in error_msg or "Missing required permissions" in error_msg:
                            logger.warning(f"Permission denied (403) for store {store.shop_url} (user {user_id}) - missing required scopes")
                            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Permission denied</div><div style='margin-bottom: 12px;'>Your store connection is missing required permissions. Please disconnect and reconnect your store to grant the necessary access.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Reconnect Store →</a></div></div>"}
                        return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Shopify error</div><div style='margin-bottom: 12px;'>{orders_data['error']}</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
                    # Otherwise, we've fetched all available orders
                    break
                
                orders = orders_data.get('orders', [])
                if not orders or len(orders) == 0:
                    break
                
                # CRITICAL: Memory management - limit total orders to prevent segfaults
                # Reduced limit to 5000 orders to prevent segfaults (code 139)
                MAX_ORDERS = 5000
                if len(all_orders_raw) + len(orders) > MAX_ORDERS:
                    logger.warning(f"Reached memory limit ({MAX_ORDERS} orders). Stopping pagination to prevent segfault.")
                    remaining = MAX_ORDERS - len(all_orders_raw)
                    if remaining > 0:
                        all_orders_raw.extend(orders[:remaining])
                    # Force garbage collection when hitting memory limit
                    import gc
                    gc.collect()
                    break
                
                # CRITICAL: Periodic garbage collection during pagination to prevent memory buildup
                if iteration % 5 == 0 and len(all_orders_raw) > 1000:
                    import gc
                    gc.collect()
                    logger.debug(f"Memory cleanup after {iteration + 1} iterations ({len(all_orders_raw)} orders)")
                
                all_orders_raw.extend(orders)
                logger.info(f"Fetched {len(orders)} orders (iteration {iteration + 1}), total so far: {len(all_orders_raw)}")
                
                # Periodic memory cleanup for large datasets
                if iteration > 0 and iteration % 5 == 0 and len(all_orders_raw) > 2000:
                    import gc
                    gc.collect()
                    logger.debug(f"Memory cleanup: Collected garbage after {iteration + 1} iterations ({len(all_orders_raw)} orders)")
                
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
                
                # CRITICAL: Explicit memory cleanup after each iteration
                # Force garbage collection for large datasets
                if iteration % 5 == 0 and len(all_orders_raw) > 1000:
                    import gc
                    gc.collect()
                    logger.debug(f"Memory cleanup after {iteration + 1} iterations")
                    
        except MemoryError:
            # CRITICAL: Handle memory errors gracefully to prevent segfaults
            logger.error(f"Memory error in generate_report for user {user_id} - clearing data")
            all_orders_raw = all_orders_raw[:5000] if len(all_orders_raw) > 5000 else all_orders_raw
            import gc
            gc.collect()
            # Continue with reduced dataset
        except Exception as e:
            # If pagination fails, try fetching without pagination (all orders, may be limited)
            logger.error(f"Error in order pagination for user {user_id}: {type(e).__name__}: {str(e)}", exc_info=True)
            try:
                db.session.remove()
                orders_data = client._make_request("orders.json?status=any&limit=250")
                if "error" not in orders_data:
                    all_orders_raw = orders_data.get('orders', [])
                    logger.warning(f"Pagination failed, fetched {len(all_orders_raw)} orders without pagination")
            except Exception as fallback_error:
                logger.error(f"Fallback order fetch also failed: {fallback_error}")
                try:
                    db.session.remove()
                except Exception:
                    pass
                return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Shopify API error</div><div style='margin-bottom: 12px;'>Please try again in a moment.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
        
        # CRITICAL: Explicit memory cleanup after order fetching
        # Force garbage collection for large datasets to prevent memory leaks
        if len(all_orders_raw) > 5000:
            import gc
            gc.collect()
            logger.info(f"Memory cleanup: Collected garbage after fetching {len(all_orders_raw)} orders")

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
        
    except SystemExit:
        # Re-raise system exits (like from sys.exit())
        raise
    except BaseException as e:
        # CRITICAL: Catch ALL exceptions including segfault precursors
        # This prevents worker crashes (code 139) from corrupting the entire process
        logger.error(f"Critical error in generate_report for user {user_id}: {type(e).__name__}: {str(e)}", exc_info=True)
        # Always clean up database session to prevent connection leaks
        try:
            db.session.rollback()
        except Exception:
            pass
        finally:
            try:
                db.session.remove()
            except Exception:
                pass
        return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Unexpected error</div><div style='margin-bottom: 12px;'>Please try again in a moment.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
