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
        
        # CRITICAL: Use GraphQL instead of REST to bypass protected customer data restrictions
        # GraphQL API doesn't have the same approval requirements as REST
        from shopify_graphql import ShopifyGraphQLClient
        graphql_client = ShopifyGraphQLClient(store.shop_url, access_token)
        
        # Initialize accumulators
        total_revenue = 0.0
        product_revenue = {}
        total_orders_count = 0
        total_orders_processed = 0
        
        # Memory-safe pagination with GraphQL
        try:
            cursor = None
            has_next_page = True
            iteration = 0
            max_iterations = 40  # Support up to ~10,000 orders
            
            while has_next_page and iteration < max_iterations:
                # Fetch batch using GraphQL
                result = graphql_client.get_orders(limit=250, cursor=cursor)
                
                if 'error' in result:
                    # Handle errors
                    if iteration == 0:
                        error_msg = result['error']
                        if 'authentication' in error_msg.lower() or '401' in error_msg:
                            logger.warning(f"Authentication failed for store {store.shop_url} (user {user_id}) - Check Scopes/Token")
                            # DO NOT disable store automatically - could be temporary
                            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication Issue</div><div style='margin-bottom: 12px;'>We couldn't verify your store access. Please try reconnecting.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Reconnect Store →</a></div></div>"}
                            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #ef4444; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #7f1d1d; margin-bottom: 8px;'>Shopify API Error</div><div style='margin-bottom: 12px;'>" + error_msg + "</div><div style='font-size: 12px; color: #737373;'>Please try again later or contact support.</div></div></div>"}
                        return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading revenue</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #ef4444; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #7f1d1d; margin-bottom: 8px;'>Shopify API Error</div><div style='margin-bottom: 12px;'>" + error_msg + "</div></div></div>"}
                    break
                
                # Extract orders from GraphQL response
                orders_data = result.get('orders', {})
                edges = orders_data.get('edges', [])
                
                if not edges:
                    break
                
                # Process batch IMMEDIATELY (Incremental Calculation)
                batch_paid_count = 0
                for edge in edges:
                    order = edge['node']
                    total_orders_processed += 1
                    
                    # Filter for paid orders (GraphQL uses displayFinancialStatus)
                    financial_status = order.get('displayFinancialStatus', '').upper()
                    if financial_status == 'PAID':
                        batch_paid_count += 1
                        
                        # Add to total revenue
                        try:
                            price_set = order.get('totalPriceSet', {})
                            shop_money = price_set.get('shopMoney', {})
                            order_total = float(shop_money.get('amount', 0))
                            total_revenue += order_total
                        except (ValueError, TypeError):
                            continue
                        
                        # Update product breakdown
                        line_items = order.get('lineItems', {}).get('edges', [])
                        for item_edge in line_items:
                            item = item_edge['node']
                            product_name = item.get('title', 'Unknown')
                            try:
                                price_set = item.get('originalUnitPriceSet', {})
                                shop_money = price_set.get('shopMoney', {})
                                price = float(shop_money.get('amount', 0))
                                quantity = int(item.get('quantity', 1))
                                revenue = price * quantity
                                
                                if product_name in product_revenue:
                                    product_revenue[product_name] += revenue
                                else:
                                    product_revenue[product_name] = revenue
                            except (ValueError, TypeError):
                                continue
                
                total_orders_count += batch_paid_count
                logger.debug(f"Processed batch {iteration+1}: {len(edges)} orders checked, {batch_paid_count} paid. Total paid so far: {total_orders_count}")
                
                # Discard batch (memory management)
                del edges
                if iteration % 5 == 0:
                    import gc
                    gc.collect()
                
                # Prepare next page
                page_info = orders_data.get('pageInfo', {})
                has_next_page = page_info.get('hasNextPage', False)
                cursor = page_info.get('endCursor')
                iteration += 1

        except Exception as e:
            logger.error(f"Error in GraphQL streaming aggregation: {e}", exc_info=True)
            # Continue with whatever data we managed to aggregate
        
        logger.info(f"Report generation complete. Scanned {total_orders_processed} orders, found {total_orders_count} paid.")
        
        # Sort products by revenue
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
        
        
        # Prepare data for report generation (MUST be before HTML uses it)
        total_orders = total_orders_count
        
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
