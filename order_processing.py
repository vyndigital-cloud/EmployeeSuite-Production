"""
Simple order processing
"""

import logging

from models import ShopifyStore
from shopify_integration import ShopifyClient

logger = logging.getLogger(__name__)


def process_orders(user_id=None):
    """Process orders for user"""
    try:
        # Get user's store
        store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
        if not store:
            return {"success": False, "error": "No store connected"}

        # Get orders from Shopify
        client = ShopifyClient(store.shop_url, store.get_access_token())
        orders = client.get_orders()

        if isinstance(orders, dict) and "error" in orders:
            return {"success": False, "error": orders["error"]}

        # Format response
        if orders:
            html = f"<h3>Found {len(orders)} orders</h3>"
            for order in orders[:10]:  # Show first 10
                html += f"<div>Order #{order['id']}: {order['customer']} - {order['total']}</div>"
        else:
            html = "<p>No orders found</p>"

        return {"success": True, "html": html}

    except Exception as e:
        logger.error(f"Error processing orders: {e}")
        return {"success": False, "error": str(e)}
