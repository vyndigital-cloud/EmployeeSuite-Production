"""
Simple inventory management
"""

import logging

from models import ShopifyStore
from shopify_integration import ShopifyClient

logger = logging.getLogger(__name__)


def update_inventory(user_id=None):
    """Update inventory for user"""
    try:
        # Get user's store
        store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
        if not store:
            return {"success": False, "error": "No store connected"}

        # Get inventory from Shopify
        client = ShopifyClient(store.shop_url, store.get_access_token())
        inventory = client.get_products()

        if isinstance(inventory, dict) and "error" in inventory:
            return {"success": False, "error": inventory["error"]}

        # Format response
        if inventory:
            html = f"<h3>Found {len(inventory)} products</h3>"
            for item in inventory[:10]:  # Show first 10
                html += f"<div>{item['product']}: {item['stock']} units at {item['price']}</div>"
        else:
            html = "<p>No inventory found</p>"

        return {"success": True, "html": html}

    except Exception as e:
        logger.error(f"Error updating inventory: {e}")
        return {"success": False, "error": str(e)}
