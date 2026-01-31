from shopify_integration import ShopifyClient
from flask_login import current_user
from models import ShopifyStore
import requests

def process_orders(creds_path='creds.json', user_id=None):
    # CRITICAL: Accept user_id as parameter to prevent recursion from accessing current_user
    # This prevents "maximum recursion depth exceeded" errors
    try:
        # Get user_id - either from parameter or safely from current_user
        if user_id is None:
            try:
                if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
                    return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication required</div><div style='margin-bottom: 12px;'>Please log in to access this feature.</div><a href='/login' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Log In →</a></div></div>"}
                # Store user_id immediately to prevent recursion
                user_id = getattr(current_user, 'id', None)
            except (RuntimeError, AttributeError, RecursionError) as e:
                return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication error</div><div style='margin-bottom: 12px;'>Please refresh the page and try again.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}

        if not user_id:
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Authentication required</div><div style='margin-bottom: 12px;'>Please log in to access this feature.</div><a href='/login' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Log In →</a></div></div>"}

        store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()

        if not store:
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>No Shopify store connected</div><div style='margin-bottom: 12px;'>Connect your store to view and manage orders.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Connect Store →</a></div></div>"}

        # Get decrypted access token
        access_token = store.get_access_token()
        if not access_token:
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Store not properly connected</div><div style='margin-bottom: 12px;'>Missing or invalid access token. Please reconnect your store.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Reconnect Store →</a></div></div>"}

        # Use GraphQL to fetch orders (bypasses protected customer data restrictions)
        try:
            from shopify_graphql import ShopifyGraphQLClient
            graphql_client = ShopifyGraphQLClient(store.shop_url, access_token)
            
            # Fetch orders with GraphQL - get orders from last 60 days
            from datetime import datetime, timedelta
            created_at_min = (datetime.utcnow() - timedelta(days=60)).isoformat()
            
            # GraphQL query for pending/unfulfilled orders
            query = """
            query getOrders($first: Int!, $query: String, $after: String) {
                orders(first: $first, query: $query, after: $after) {
                    edges {
                        node {
                            id
                            name
                            createdAt
                            totalPriceSet {
                                shopMoney {
                                    amount
                                }
                            }
                            displayFinancialStatus
                            displayFulfillmentStatus
                        }
                        cursor
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
            """
            
            # Fetch pending and unfulfilled orders
            all_orders = []
            order_ids = set()
            
            # Query for pending orders OR unfulfilled orders
            query_filter = f"created_at:>'{created_at_min}' AND (financial_status:pending OR fulfillment_status:unfulfilled)"
            variables = {"first": 250, "query": query_filter}
            
            result = graphql_client.execute_query(query, variables)
            if result and 'data' in result and 'orders' in result['data']:
                for edge in result['data']['orders']['edges']:
                    order = edge['node']
                    order_id = order.get('id')
                    if order_id not in order_ids:
                        # Transform GraphQL response to match expected format
                        transformed_order = {
                            'id': order_id,
                            'name': order.get('name', 'N/A'),
                            'total_price': order.get('totalPriceSet', {}).get('shopMoney', {}).get('amount', '0'),
                            'financial_status': order.get('displayFinancialStatus', '').lower(),
                            'fulfillment_status': order.get('displayFulfillmentStatus', '').lower()
                        }
                        all_orders.append(transformed_order)
                        order_ids.add(order_id)
            
        except requests.exceptions.Timeout:
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Connection timeout</div><div style='margin-bottom: 12px;'>Shopify API is taking too long to respond. Please try again in a moment.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Connection error</div><div style='margin-bottom: 12px;'>Cannot connect to Shopify. Check your internet connection and verify your store is connected.</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
        except Exception as e:
            return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Shopify API error</div><div style='margin-bottom: 12px;'>{str(e)}</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}



        # Build minimalistic HTML output with unified style (same as inventory/reports)
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        # Unified minimalistic style
        html = f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'>"
        
        # Title row - Match Gen Report structure (Flex container)
        html += f"<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; width: 100%;'>"
        html += f"<div style='font-size: 13px; font-weight: 600; color: #171717; flex: 1;'>Pending Orders ({len(all_orders)})</div>"
        html += f"</div>"

        # Summary box - Match Gen Report structure (Nested divs, 2 lines)
        if len(all_orders) == 0:
             html += f"<div style='padding: 8px 12px; background: #f0fdf4; border-left: 2px solid #16a34a; border-radius: 4px; margin-bottom: 12px;'>"
             html += f"<div style='font-weight: 600; color: #166534; font-size: 12px;'>All orders processed</div>"
             html += f"<div style='color: #166534; font-size: 11px; margin-top: 2px;'>You're all caught up!</div>"
             html += f"</div>"
        else:
             html += f"<div style='padding: 8px 12px; background: #fffbeb; border-left: 2px solid #f59e0b; border-radius: 4px; margin-bottom: 12px;'>"
             html += f"<div style='font-weight: 600; color: #92400e; font-size: 12px;'>Action Required</div>"
             html += f"<div style='color: #92400e; font-size: 11px; margin-top: 2px;'>{len(all_orders)} orders need attention</div>"
             html += f"</div>"

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

            html += f"<div style='padding: 10px 12px; margin: 6px 0; background: #fff; border-left: 2px solid {border_color}; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;'><div style='flex: 1;'><div style='font-weight: 500; color: #171717; font-size: 13px;'>{order_name}</div><div style='color: #737373; margin-top: 2px; font-size: 11px;'>{status_text}</div></div><div style='text-align: right; margin-left: 16px;'><div style='font-weight: 600; color: {border_color}; font-size: 13px;'>${total}</div></div></div>"

        html += f"<div style='color: #a3a3a3; font-size: 10px; margin-top: 12px; text-align: right;'>Updated: {timestamp}</div>"
        html += "</div>"

        return {"success": True, "message": html}

    except Exception as e:
        return {"success": False, "error": f"<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif;'><div style='font-size: 13px; font-weight: 600; color: #171717; margin-bottom: 8px;'>Error Loading orders</div><div style='padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6;'><div style='font-weight: 600; color: #202223; margin-bottom: 8px;'>Unexpected error</div><div style='margin-bottom: 12px;'>{str(e)}</div><a href='/settings/shopify' style='display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;'>Check Settings →</a></div></div>"}
