"""
Simple reporting
"""

import logging

from models import ShopifyStore
from shopify_integration import ShopifyClient

logger = logging.getLogger(__name__)


def generate_report(user_id=None, shop_url=None):
    """Generate revenue report for user"""
    try:
        # Get user's store
        store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
        if not store:
            return {"success": False, "error": "No store connected"}

        # Get orders from Shopify for revenue calculation
        client = ShopifyClient(store.shop_url, store.get_access_token())
        orders = client.get_orders()

        if isinstance(orders, dict) and "error" in orders:
            return {"success": False, "error": orders["error"]}

        # Calculate revenue
        total_revenue = 0
        if orders:
            for order in orders:
                try:
                    # Extract numeric value from total (remove $ and convert)
                    total_str = (
                        order.get("total", "$0").replace("$", "").replace(",", "")
                    )
                    total_revenue += float(total_str)
                except (ValueError, TypeError):
                    continue

        # Format response
        avg_value = total_revenue / len(orders) if orders else 0
        
        html = f"""
        <div class="output-card">
            <div class="output-header">
                <h4>Revenue Overview</h4>
                <span class="badge badge-primary">Today</span>
            </div>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-label">Total Orders</div>
                    <div class="stat-value">{len(orders) if orders else 0}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Total Revenue</div>
                    <div class="stat-value">${total_revenue:,.2f}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Avg. Order Value</div>
                    <div class="stat-value">${avg_value:,.2f}</div>
                </div>
            </div>
        </div>
        """

        return {"success": True, "html": html}

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return {"success": False, "error": str(e)}


def generate_orders_report(user_id=None, start_date=None, end_date=None):
    """Generate orders report"""
    try:
        store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
        if not store:
            return {"success": False, "error": "No store connected"}

        client = ShopifyClient(store.shop_url, store.get_access_token())
        orders = client.get_orders(start_date=start_date, end_date=end_date)

        if isinstance(orders, dict) and "error" in orders:
            return {"success": False, "error": orders["error"]}

        # Process orders data
        total_orders = len(orders) if orders else 0
        total_revenue = 0
        pending_orders = 0
        fulfilled_orders = 0

        if orders:
            for order in orders:
                try:
                    total_str = order.get("total", "$0").replace("$", "").replace(",", "")
                    total_revenue += float(total_str)
                except (ValueError, TypeError):
                    continue
                
                status = order.get('fulfillment_status', 'pending')
                if status == 'fulfilled':
                    fulfilled_orders += 1
                else:
                    pending_orders += 1

        html = f"""
        <div class="output-card">
            <div class="output-header">
                <h4>Orders Overview</h4>
                <span class="badge badge-primary">Recent</span>
            </div>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-label">Total Orders</div>
                    <div class="stat-value">{total_orders}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Total Revenue</div>
                    <div class="stat-value">${total_revenue:,.2f}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Fulfilled</div>
                    <div class="stat-value">{fulfilled_orders}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Pending</div>
                    <div class="stat-value">{pending_orders}</div>
                </div>
            </div>
        </div>
        """

        return {"success": True, "html": html, "data": {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "fulfilled_orders": fulfilled_orders,
            "pending_orders": pending_orders
        }}

    except Exception as e:
        logger.error(f"Error generating orders report: {e}")
        return {"success": False, "error": str(e)}


def generate_inventory_report(user_id=None):
    """Generate inventory report"""
    try:
        store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
        if not store:
            return {"success": False, "error": "No store connected"}

        client = ShopifyClient(store.shop_url, store.get_access_token())
        products = client.get_products()

        if isinstance(products, dict) and "error" in products:
            return {"success": False, "error": products["error"]}

        # Process inventory data
        total_products = len(products) if products else 0
        low_stock_items = 0
        out_of_stock_items = 0
        total_inventory = 0

        if products:
            for product in products:
                for variant in product.get('variants', []):
                    inventory = variant.get('inventory_quantity', 0)
                    total_inventory += inventory
                    
                    if inventory == 0:
                        out_of_stock_items += 1
                    elif inventory <= 5:
                        low_stock_items += 1

        html = f"""
        <div class="output-card">
            <div class="output-header">
                <h4>Inventory Overview</h4>
                <span class="badge badge-info">Current</span>
            </div>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-label">Total Products</div>
                    <div class="stat-value">{total_products}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Total Inventory</div>
                    <div class="stat-value">{total_inventory}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Low Stock</div>
                    <div class="stat-value">{low_stock_items}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Out of Stock</div>
                    <div class="stat-value">{out_of_stock_items}</div>
                </div>
            </div>
        </div>
        """

        return {"success": True, "html": html, "data": {
            "total_products": total_products,
            "total_inventory": total_inventory,
            "low_stock_items": low_stock_items,
            "out_of_stock_items": out_of_stock_items
        }}

    except Exception as e:
        logger.error(f"Error generating inventory report: {e}")
        return {"success": False, "error": str(e)}
