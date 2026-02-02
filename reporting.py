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
        html = f"<h3>Revenue Report</h3>"
        html += f"<p>Total Orders: {len(orders) if orders else 0}</p>"
        html += f"<p>Total Revenue: ${total_revenue:,.2f}</p>"

        return {"success": True, "html": html}

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return {"success": False, "error": str(e)}
