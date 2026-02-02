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
