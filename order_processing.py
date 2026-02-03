"""
Production-ready order processing with real Shopify integration
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from models import ShopifyStore
from shopify_integration import ShopifyClient

logger = logging.getLogger(__name__)


def process_orders(user_id=None, start_date=None, end_date=None, **kwargs):
    """Process orders for user with comprehensive analytics and error handling"""
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

        # Get orders from Shopify with comprehensive error handling
        client = ShopifyClient(store.shop_url, access_token)
        
        try:
            orders = client.get_orders(
                status="any", 
                limit=250, 
                start_date=start_date, 
                end_date=end_date
            )
            
            # Handle API errors
            if isinstance(orders, dict) and "error" in orders:
                error_msg = orders["error"]
                
                # Handle specific error types
                if orders.get("permission_denied"):
                    return {
                        "success": False,
                        "error": "Missing permissions to access order data. Please reinstall the app.",
                        "action": "reinstall",
                        "technical_details": error_msg
                    }
                elif orders.get("auth_failed"):
                    return {
                        "success": False,
                        "error": "Authentication failed. Please reconnect your store.",
                        "action": "reconnect",
                        "technical_details": error_msg
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Unable to fetch orders: {error_msg}",
                        "action": "retry"
                    }
            
            # Ensure orders is a list
            if not isinstance(orders, list):
                logger.error(f"Unexpected orders response type: {type(orders)}")
                return {"success": False, "error": "Invalid response from Shopify API"}

        except Exception as api_error:
            logger.error(f"Shopify API error for user {user_id}: {api_error}")
            return {
                "success": False,
                "error": "Failed to connect to Shopify. Please try again.",
                "technical_details": str(api_error)[:100],
                "action": "retry"
            }

        # Process orders with comprehensive analytics
        if orders:
            # Calculate metrics
            total_orders = len(orders)
            total_revenue = 0
            pending_orders = 0
            fulfilled_orders = 0
            high_value_orders = 0
            recent_orders = []
            
            # Process each order
            for order in orders:
                try:
                    # Safely extract order total
                    order_total = 0
                    try:
                        total_price = order.get('total_price', '0')
                        if isinstance(total_price, str):
                            # Remove currency symbols and convert
                            total_price = total_price.replace('$', '').replace(',', '')
                        order_total = float(total_price)
                    except (ValueError, TypeError):
                        order_total = 0
                    
                    total_revenue += order_total
                    
                    # Count order statuses
                    fulfillment_status = order.get('fulfillment_status', 'unfulfilled')
                    if fulfillment_status in ['unfulfilled', 'partial']:
                        pending_orders += 1
                    else:
                        fulfilled_orders += 1
                    
                    # Count high-value orders
                    if order_total > 100:
                        high_value_orders += 1
                    
                    # Format customer name safely
                    customer = order.get('customer', {}) or {}
                    first_name = customer.get('first_name', '') or ''
                    last_name = customer.get('last_name', '') or ''
                    customer_name = f"{first_name} {last_name}".strip()
                    if not customer_name:
                        customer_name = "Guest Customer"
                    
                    # Add to recent orders for display
                    recent_orders.append({
                        "id": order.get('id', 'N/A'),
                        "order_number": order.get('order_number', order.get('name', 'N/A')),
                        "customer": customer_name,
                        "total": f"${order_total:.2f}",
                        "currency": order.get('currency', 'USD'),
                        "status": order.get('financial_status', 'unknown').title(),
                        "fulfillment": fulfillment_status.title(),
                        "date": order.get('created_at', '')[:10] if order.get('created_at') else 'N/A',
                        "items": len(order.get('line_items', []))
                    })
                    
                except Exception as order_error:
                    logger.warning(f"Error processing individual order: {order_error}")
                    continue
            
            # Calculate additional metrics
            avg_order_value = round(total_revenue / total_orders, 2) if total_orders > 0 else 0
            fulfillment_rate = round((fulfilled_orders / total_orders) * 100, 1) if total_orders > 0 else 0
            
            # Generate insights
            insights = []
            if pending_orders > 0:
                insights.append(f"⚠️ {pending_orders} orders need fulfillment")
            else:
                insights.append("✅ All orders are fulfilled")
            
            if avg_order_value > 75:
                insights.append(f"📈 Strong AOV: ${avg_order_value}")
            elif avg_order_value > 0:
                insights.append(f"💡 AOV opportunity: ${avg_order_value} (target: $75+)")
            
            if high_value_orders > 0:
                insights.append(f"💎 {high_value_orders} high-value orders ($100+)")
            
            # Generate professional HTML output
            html = f"""
            <div class="output-card">
                <div class="output-header">
                    <h4>📦 Order Analysis</h4>
                    <span class="badge badge-success">Live Data</span>
                </div>
                
                <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin: 20px 0;">
                    <div class="stat-box">
                        <div class="stat-label">Total Orders</div>
                        <div class="stat-value" style="color: #008060;">{total_orders}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Total Revenue</div>
                        <div class="stat-value" style="color: #008060;">${total_revenue:,.2f}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Avg Order Value</div>
                        <div class="stat-value" style="color: #008060;">${avg_order_value}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Fulfillment Rate</div>
                        <div class="stat-value" style="color: {'#16a34a' if fulfillment_rate > 80 else '#f59e0b' if fulfillment_rate > 50 else '#dc2626'};">{fulfillment_rate}%</div>
                    </div>
                </div>
                
                <div class="insights-section" style="background: #f8f9fa; padding: 16px; border-radius: 8px; margin: 20px 0;">
                    <h5 style="margin: 0 0 12px 0; color: #374151;">📊 Key Insights</h5>
                    <ul style="margin: 0; padding-left: 20px;">
                        {''.join([f'<li style="margin-bottom: 4px;">{insight}</li>' for insight in insights])}
                    </ul>
                </div>
                
                <div class="table-responsive">
                    <table class="premium-table" style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background-color: #f8f9fa;">
                                <th style="padding: 12px 8px; text-align: left; border-bottom: 2px solid #e5e7eb;">Order</th>
                                <th style="padding: 12px 8px; text-align: left; border-bottom: 2px solid #e5e7eb;">Customer</th>
                                <th style="padding: 12px 8px; text-align: left; border-bottom: 2px solid #e5e7eb;">Total</th>
                                <th style="padding: 12px 8px; text-align: left; border-bottom: 2px solid #e5e7eb;">Status</th>
                                <th style="padding: 12px 8px; text-align: left; border-bottom: 2px solid #e5e7eb;">Date</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            # Add recent orders to table (limit to 15 for performance)
            for order in recent_orders[:15]:
                status_color = "#16a34a" if order['fulfillment'] == "Fulfilled" else "#f59e0b"
                html += f"""
                            <tr style="border-bottom: 1px solid #e5e7eb;">
                                <td style="padding: 10px 8px;">
                                    <strong>#{order['order_number']}</strong>
                                    <br><small style="color: #6b7280;">{order['items']} items</small>
                                </td>
                                <td style="padding: 10px 8px;">{order['customer']}</td>
                                <td style="padding: 10px 8px;">
                                    <strong style="color: #008060;">{order['total']}</strong>
                                </td>
                                <td style="padding: 10px 8px;">
                                    <span style="color: {status_color}; font-weight: 500;">{order['fulfillment']}</span>
                                    <br><small style="color: #6b7280;">{order['status']}</small>
                                </td>
                                <td style="padding: 10px 8px;">{order['date']}</td>
                            </tr>
                """
            
            html += """
                        </tbody>
                    </table>
                </div>
                
                <div style="margin-top: 16px; padding: 12px; background: #f0f9ff; border-radius: 6px; border-left: 4px solid #008060;">
                    <small style="color: #374151;">
                        📊 <strong>Pro Tip:</strong> Orders with fulfillment rates above 90% typically see 25% higher customer retention.
                        {' Focus on fulfilling pending orders quickly.' if pending_orders > 0 else ' Great job maintaining high fulfillment rates!'}
                    </small>
                </div>
            </div>
            """
            
            return {
                "success": True, 
                "html": html,
                "data": {
                    "total_orders": total_orders,
                    "total_revenue": total_revenue,
                    "pending_orders": pending_orders,
                    "fulfilled_orders": fulfilled_orders,
                    "avg_order_value": avg_order_value,
                    "fulfillment_rate": fulfillment_rate,
                    "high_value_orders": high_value_orders
                }
            }
        else:
            # No orders found
            date_range_text = ""
            if start_date or end_date:
                if start_date and end_date:
                    date_range_text = f" between {start_date} and {end_date}"
                elif start_date:
                    date_range_text = f" since {start_date}"
                elif end_date:
                    date_range_text = f" before {end_date}"
            
            html = f"""
            <div class="output-card">
                <div class="output-header">
                    <h4>📦 Order Analysis</h4>
                    <span class="badge badge-info">No Data</span>
                </div>
                <div style="padding: 40px 24px; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 16px;">📭</div>
                    <h5 style="color: #374151; margin-bottom: 8px;">No Orders Found</h5>
                    <p style="color: #6b7280; margin-bottom: 20px;">
                        No orders were found{date_range_text}. This could mean:
                    </p>
                    <ul style="text-align: left; color: #6b7280; max-width: 300px; margin: 0 auto;">
                        <li>Your store is new and hasn't received orders yet</li>
                        <li>The date range selected has no orders</li>
                        <li>Orders might be in a different status</li>
                    </ul>
                    <div style="margin-top: 24px;">
                        <small style="color: #9ca3af;">
                            💡 <strong>Tip:</strong> Try expanding your date range or check your Shopify admin for recent activity.
                        </small>
                    </div>
                </div>
            </div>
            """
            
            return {
                "success": True, 
                "html": html,
                "data": {
                    "total_orders": 0,
                    "total_revenue": 0,
                    "pending_orders": 0,
                    "fulfilled_orders": 0,
                    "avg_order_value": 0,
                    "fulfillment_rate": 0,
                    "high_value_orders": 0
                }
            }

    except Exception as e:
        logger.error(f"Error processing orders for user {user_id}: {e}", exc_info=True)
        return {
            "success": False, 
            "error": "An unexpected error occurred while processing orders.",
            "technical_details": str(e)[:100],
            "action": "retry"
        }
