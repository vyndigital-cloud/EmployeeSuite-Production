"""
Production-ready reporting with real Shopify integration and advanced analytics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import uuid
from models import ShopifyStore, UsageEvent, db
from shopify_integration import ShopifyClient

logger = logging.getLogger(__name__)


def generate_report(user_id=None, shop_url=None, start_date=None, end_date=None):
    """Generate comprehensive revenue report with advanced analytics"""
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

        # Set default date range if not provided (last 30 days)
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        if not end_date:
            end_date = datetime.utcnow().isoformat()

        # Get orders from Shopify for revenue calculation
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
                        "error": f"Unable to fetch revenue data: {error_msg}",
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

        # Process orders for comprehensive revenue analytics
        if orders:
            # Initialize analytics
            total_revenue = 0
            total_orders = len(orders)
            product_revenue = {}
            daily_revenue = {}
            customer_revenue = {}
            payment_methods = {}
            
            # Process each order
            for order in orders:
                try:
                    # Safely extract order total
                    order_total = 0
                    try:
                        total_price = order.get('total_price', '0')
                        if isinstance(total_price, str):
                            total_price = total_price.replace('$', '').replace(',', '')
                        order_total = float(total_price)
                    except (ValueError, TypeError):
                        order_total = 0
                    
                    total_revenue += order_total
                    
                    # Daily revenue breakdown
                    created_at = order.get('created_at', '')
                    if created_at:
                        try:
                            # Parse ISO date
                            if 'T' in created_at:
                                order_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
                            else:
                                order_date = datetime.strptime(created_at[:10], '%Y-%m-%d').date()
                            
                            date_str = order_date.strftime('%Y-%m-%d')
                            daily_revenue[date_str] = daily_revenue.get(date_str, 0) + order_total
                        except Exception as date_error:
                            logger.warning(f"Error parsing date {created_at}: {date_error}")
                    
                    # Customer revenue analysis
                    customer = order.get('customer', {}) or {}
                    customer_email = customer.get('email', '') or order.get('email', 'guest@unknown.com')
                    customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
                    if not customer_name:
                        customer_name = "Guest Customer"
                    
                    customer_key = f"{customer_name} ({customer_email})"
                    if customer_key not in customer_revenue:
                        customer_revenue[customer_key] = {"revenue": 0, "orders": 0}
                    customer_revenue[customer_key]["revenue"] += order_total
                    customer_revenue[customer_key]["orders"] += 1
                    
                    # Payment method analysis
                    gateway = order.get('gateway', 'Unknown')
                    payment_methods[gateway] = payment_methods.get(gateway, 0) + order_total
                    
                    # Product revenue breakdown
                    for line_item in order.get('line_items', []):
                        try:
                            product_name = line_item.get('title', 'Unknown Product')
                            quantity = int(line_item.get('quantity', 1))
                            
                            # Calculate line item total
                            item_price = 0
                            try:
                                price_str = line_item.get('price', '0')
                                if isinstance(price_str, str):
                                    price_str = price_str.replace('$', '').replace(',', '')
                                item_price = float(price_str)
                            except (ValueError, TypeError):
                                item_price = 0
                            
                            line_total = item_price * quantity
                            
                            if product_name not in product_revenue:
                                product_revenue[product_name] = {"revenue": 0, "quantity": 0, "orders": 0}
                            
                            product_revenue[product_name]["revenue"] += line_total
                            product_revenue[product_name]["quantity"] += quantity
                            product_revenue[product_name]["orders"] += 1
                            
                        except Exception as line_error:
                            logger.warning(f"Error processing line item: {line_error}")
                            continue
                    
                except Exception as order_error:
                    logger.warning(f"Error processing order: {order_error}")
                    continue
            
            # Calculate advanced metrics
            avg_order_value = round(total_revenue / total_orders, 2) if total_orders > 0 else 0
            
            # Sort data for insights
            top_products = sorted(product_revenue.items(), key=lambda x: x[1]["revenue"], reverse=True)[:10]
            top_customers = sorted(customer_revenue.items(), key=lambda x: x[1]["revenue"], reverse=True)[:10]
            top_payment_methods = sorted(payment_methods.items(), key=lambda x: x[1], reverse=True)
            
            # Calculate daily trends
            sorted_daily = sorted(daily_revenue.items())
            daily_trend = "stable"
            if len(sorted_daily) >= 2:
                recent_avg = sum(daily_revenue[date] for date in list(daily_revenue.keys())[-7:]) / min(7, len(daily_revenue))
                earlier_avg = sum(daily_revenue[date] for date in list(daily_revenue.keys())[:-7]) / max(1, len(daily_revenue) - 7)
                
                if recent_avg > earlier_avg * 1.1:
                    daily_trend = "increasing"
                elif recent_avg < earlier_avg * 0.9:
                    daily_trend = "decreasing"
            
            # Generate insights
            insights = []
            
            if total_revenue > 0:
                insights.append(f"💰 Generated ${total_revenue:,.2f} in revenue from {total_orders} orders")
                insights.append(f"📊 Average order value: ${avg_order_value}")
                
                if daily_trend == "increasing":
                    insights.append("📈 Revenue trend is increasing - great momentum!")
                elif daily_trend == "decreasing":
                    insights.append("📉 Revenue trend is decreasing - consider marketing campaigns")
                else:
                    insights.append("📊 Revenue trend is stable")
                
                if top_products:
                    top_product_name, top_product_data = top_products[0]
                    insights.append(f"🏆 Top product: {top_product_name} (${top_product_data['revenue']:,.2f})")
                
                if avg_order_value > 100:
                    insights.append("💎 Excellent average order value - customers are buying premium items")
                elif avg_order_value > 50:
                    insights.append("✅ Good average order value - consider upselling opportunities")
                else:
                    insights.append("💡 Consider bundling products to increase average order value")
            
            # Generate professional HTML report
            html = f"""
            <div class="output-card">
                <div class="output-header">
                    <h4>💰 Revenue Analytics</h4>
                    <span class="badge badge-success">Live Data</span>
                </div>
                
                <div class="date-range" style="background: #f8f9fa; padding: 12px; border-radius: 6px; margin-bottom: 20px; text-align: center;">
                    <small style="color: #6b7280;">
                        📅 Report Period: {start_date[:10] if start_date else 'N/A'} to {end_date[:10] if end_date else 'N/A'}
                    </small>
                </div>
                
                <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin: 20px 0;">
                    <div class="stat-box">
                        <div class="stat-label">Total Revenue</div>
                        <div class="stat-value" style="color: #008060; font-size: 24px;">${total_revenue:,.2f}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Total Orders</div>
                        <div class="stat-value" style="color: #008060; font-size: 24px;">{total_orders}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Avg Order Value</div>
                        <div class="stat-value" style="color: #008060; font-size: 24px;">${avg_order_value}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Revenue Trend</div>
                        <div class="stat-value" style="color: {'#16a34a' if daily_trend == 'increasing' else '#f59e0b' if daily_trend == 'decreasing' else '#6b7280'}; font-size: 18px;">
                            {'📈 Up' if daily_trend == 'increasing' else '📉 Down' if daily_trend == 'decreasing' else '📊 Stable'}
                        </div>
                    </div>
                </div>
                
                <div class="insights-section" style="background: #f8f9fa; padding: 16px; border-radius: 8px; margin: 20px 0;">
                    <h5 style="margin: 0 0 12px 0; color: #374151;">📊 Key Insights</h5>
                    <ul style="margin: 0; padding-left: 20px;">
                        {''.join([f'<li style="margin-bottom: 4px;">{insight}</li>' for insight in insights])}
                    </ul>
                </div>
            """
            
            # Add top products section
            if top_products:
                html += """
                <div class="top-products" style="margin: 20px 0;">
                    <h5 style="color: #374151; margin-bottom: 16px;">🏆 Top Products by Revenue</h5>
                    <div style="background: white; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;">
                """
                
                for i, (product_name, product_data) in enumerate(top_products[:5]):
                    revenue_percentage = (product_data["revenue"] / total_revenue) * 100 if total_revenue > 0 else 0
                    html += f"""
                        <div style="padding: 12px 16px; border-bottom: 1px solid #f3f4f6; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-weight: 600; color: #111827;">{product_name}</div>
                                <div style="font-size: 12px; color: #6b7280;">{product_data['quantity']} units sold • {product_data['orders']} orders</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-weight: 600; color: #008060;">${product_data['revenue']:,.2f}</div>
                                <div style="font-size: 12px; color: #6b7280;">{revenue_percentage:.1f}% of total</div>
                            </div>
                        </div>
                    """
                
                html += "</div></div>"
            
            # Add daily revenue chart data (simplified)
            if daily_revenue:
                html += """
                <div class="daily-revenue" style="margin: 20px 0;">
                    <h5 style="color: #374151; margin-bottom: 16px;">📈 Daily Revenue Trend</h5>
                    <div style="background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px;">
                """
                
                max_daily = max(daily_revenue.values()) if daily_revenue else 1
                for date, revenue in sorted(daily_revenue.items())[-14:]:  # Last 14 days
                    bar_width = (revenue / max_daily) * 100 if max_daily > 0 else 0
                    html += f"""
                        <div style="display: flex; align-items: center; margin-bottom: 8px;">
                            <div style="width: 80px; font-size: 12px; color: #6b7280;">{date[5:]}</div>
                            <div style="flex: 1; background: #f3f4f6; height: 20px; border-radius: 4px; margin: 0 12px; overflow: hidden;">
                                <div style="width: {bar_width}%; height: 100%; background: #008060; border-radius: 4px;"></div>
                            </div>
                            <div style="width: 80px; text-align: right; font-size: 12px; font-weight: 600; color: #008060;">${revenue:,.0f}</div>
                        </div>
                    """
                
                html += "</div></div>"
            
            html += """
                <div style="margin-top: 16px; padding: 12px; background: #f0f9ff; border-radius: 6px; border-left: 4px solid #008060;">
                    <small style="color: #374151;">
                        📊 <strong>Pro Tip:</strong> Track your revenue trends weekly. Consistent growth of 10-20% month-over-month indicates healthy business expansion.
                    </small>
                </div>
            </div>
            """
            
            # RECORD USAGE (Passive Revenue Meter)
            record_usage_event(
                store_id=store.id,
                event_type='report_generated',
                description=f"Generated {total_orders} order report",
                price=0.01  # Metered price per report
            )

            return {
                "success": True, 
                "html": html,
                "report_data": {
                    "total_revenue": total_revenue,
                    "total_orders": total_orders,
                    "average_order_value": avg_order_value,
                    "top_products": top_products,
                    "daily_revenue": daily_revenue,
                    "top_customers": top_customers,
                    "payment_methods": top_payment_methods,
                    "revenue_trend": daily_trend
                }
            }
        else:
            # No orders found
            date_range_text = f"between {start_date[:10]} and {end_date[:10]}" if start_date and end_date else "in the selected period"
            
            html = f"""
            <div class="output-card">
                <div class="output-header">
                    <h4>💰 Revenue Analytics</h4>
                    <span class="badge badge-info">No Data</span>
                </div>
                <div style="padding: 40px 24px; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 16px;">📊</div>
                    <h5 style="color: #374151; margin-bottom: 8px;">No Revenue Data</h5>
                    <p style="color: #6b7280; margin-bottom: 20px;">
                        No orders were found {date_range_text}. This could mean:
                    </p>
                    <ul style="text-align: left; color: #6b7280; max-width: 350px; margin: 0 auto;">
                        <li>Your store is new and hasn't received orders yet</li>
                        <li>The selected date range has no completed orders</li>
                        <li>Orders might be in draft or cancelled status</li>
                        <li>There might be a temporary connection issue</li>
                    </ul>
                    <div style="margin-top: 24px;">
                        <small style="color: #9ca3af;">
                            💡 <strong>Tip:</strong> Try expanding your date range or check your Shopify admin for recent order activity.
                        </small>
                    </div>
                </div>
            </div>
            """
            
            return {
                "success": True, 
                "html": html,
                "report_data": {
                    "total_revenue": 0,
                    "total_orders": 0,
                    "average_order_value": 0,
                    "top_products": [],
                    "daily_revenue": {},
                    "top_customers": [],
                    "payment_methods": [],
                    "revenue_trend": "no_data"
                }
            }

    except Exception as e:
        logger.error(f"Error generating report for user {user_id}: {e}", exc_info=True)
        return {
            "success": False, 
            "error": "An unexpected error occurred while generating the revenue report.",
            "technical_details": str(e)[:100],
            "action": "retry"
        }


def generate_orders_report(user_id=None, start_date=None, end_date=None):
    """Generate detailed orders report with fulfillment analysis"""
    try:
        store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
        if not store:
            return {"success": False, "error": "No store connected"}

        access_token = store.get_access_token()
        if not access_token:
            return {"success": False, "error": "Store connection expired", "action": "reconnect"}

        client = ShopifyClient(store.shop_url, access_token)
        orders = client.get_orders(start_date=start_date, end_date=end_date, limit=250)

        if isinstance(orders, dict) and "error" in orders:
            return {"success": False, "error": orders["error"]}

        if not isinstance(orders, list):
            return {"success": False, "error": "Invalid response from Shopify API"}

        # Process orders data with detailed analysis
        total_orders = len(orders)
        total_revenue = 0
        pending_orders = 0
        fulfilled_orders = 0
        cancelled_orders = 0
        refunded_orders = 0

        for order in orders:
            try:
                # Revenue calculation
                order_total = 0
                try:
                    total_price = order.get('total_price', '0')
                    if isinstance(total_price, str):
                        total_price = total_price.replace('$', '').replace(',', '')
                    order_total = float(total_price)
                except (ValueError, TypeError):
                    order_total = 0
                
                total_revenue += order_total
                
                # Status analysis
                fulfillment_status = order.get('fulfillment_status', 'unfulfilled')
                financial_status = order.get('financial_status', 'pending')
                
                if fulfillment_status in ['unfulfilled', 'partial']:
                    pending_orders += 1
                elif fulfillment_status == 'fulfilled':
                    fulfilled_orders += 1
                
                if financial_status == 'refunded':
                    refunded_orders += 1
                elif 'cancelled' in str(order.get('cancelled_at', '')):
                    cancelled_orders += 1
                    
            except Exception as order_error:
                logger.warning(f"Error processing order in orders report: {order_error}")
                continue

        avg_order_value = round(total_revenue / total_orders, 2) if total_orders > 0 else 0
        fulfillment_rate = round((fulfilled_orders / total_orders) * 100, 1) if total_orders > 0 else 0

        return {
            "success": True,
            "data": {
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "fulfilled_orders": fulfilled_orders,
                "pending_orders": pending_orders,
                "cancelled_orders": cancelled_orders,
                "refunded_orders": refunded_orders,
                "average_order_value": avg_order_value,
                "fulfillment_rate": fulfillment_rate
            }
        }

    except Exception as e:
        logger.error(f"Error generating orders report: {e}")
        return {"success": False, "error": str(e)}


def generate_inventory_report(user_id=None):
    """Generate detailed inventory report with stock analysis"""
    try:
        store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
        if not store:
            return {"success": False, "error": "No store connected"}

        access_token = store.get_access_token()
        if not access_token:
            return {"success": False, "error": "Store connection expired", "action": "reconnect"}

        client = ShopifyClient(store.shop_url, access_token)
        products = client.get_products()

        if isinstance(products, dict) and "error" in products:
            return {"success": False, "error": products["error"]}

        if not isinstance(products, list):
            return {"success": False, "error": "Invalid response from Shopify API"}

        # Process inventory data with detailed analysis
        total_products = len(products)
        low_stock_items = 0
        out_of_stock_items = 0
        total_inventory_value = 0

        for product in products:
            try:
                # Stock analysis
                stock = int(product.get('stock', 0))
                
                # Price calculation
                price_value = 0
                try:
                    price_str = product.get('price', '$0.00')
                    if isinstance(price_str, str):
                        price_str = price_str.replace('$', '').replace(',', '')
                    price_value = float(price_str)
                except (ValueError, TypeError):
                    price_value = 0
                
                inventory_value = stock * price_value
                total_inventory_value += inventory_value
                
                # Stock level categorization
                if stock == 0:
                    out_of_stock_items += 1
                elif stock <= 5:
                    low_stock_items += 1
                    
            except Exception as product_error:
                logger.warning(f"Error processing product in inventory report: {product_error}")
                continue

        in_stock_items = total_products - out_of_stock_items
        stock_health_score = round(((in_stock_items - low_stock_items) / total_products) * 100, 1) if total_products > 0 else 0

        return {
            "success": True,
            "data": {
                "total_products": total_products,
                "total_inventory_value": total_inventory_value,
                "low_stock_items": low_stock_items,
                "out_of_stock_items": out_of_stock_items,
                "in_stock_items": in_stock_items,
                "stock_health_score": stock_health_score
            }
        }

    except Exception as e:
        logger.error(f"Error generating inventory report: {e}")
        return {"success": False, "error": str(e)}

def record_usage_event(store_id: int, event_type: str, description: Optional[str] = None, price: float = 0.0):
    """
    Record a billable event in the database for later sync with Shopify.
    Uses minute-level idempotency to prevent accidental double-billing.
    """
    try:
        # Minute-level idempotency key
        timestamp_key = datetime.utcnow().strftime('%Y%m%d%H%M')
        idempotency_key = f"{event_type}:{store_id}:{timestamp_key}"
        
        # Check if already recorded in this minute
        existing = UsageEvent.query.filter_by(idempotency_key=idempotency_key).first()
        if existing:
            return existing

        usage = UsageEvent(
            store_id=store_id,
            event_type=event_type,
            description=description,
            price=price,
            idempotency_key=idempotency_key
        )
        db.session.add(usage)
        db.session.commit()
        
        logger.info(f"📈 [METER] Recorded {event_type} for store {store_id}")
        return usage
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ [METER] Failed to record usage: {e}")
        return None
