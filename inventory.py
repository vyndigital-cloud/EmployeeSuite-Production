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
            html = """
            <div class="output-card">
                <div class="output-header">
                    <h4>Inventory Status</h4>
                    <span class="badge badge-warning">Low Stock Alerts</span>
                </div>
                <div class="inventory-list">
            """
            for item in inventory[:10]:  # Show first 10
                # Calculate simple percentage for demo stock bar (max 100 for visual)
                try:
                    stock_val = int(item['stock'])
                    percentage = min(100, max(0, (stock_val / 50) * 100))
                except (ValueError, TypeError):
                    stock_val = 0
                    percentage = 0
                
                html += f"""
                    <div class="inventory-item">
                        <div class="inventory-info">
                            <div class="product-name">{item['product']}</div>
                            <div class="price-text">{item['price']}</div>
                        </div>
                        <div class="inventory-stock">
                            <div class="stock-count">{stock_val} units</div>
                            <div class="stock-bar-bg">
                                <div class="stock-bar-fill" style="width: {percentage}%; background-color: #008060;"></div>
                            </div>
                        </div>
                    </div>
                """
            html += """
                </div>
            </div>
            """
        else:
            html = """
            <div class="output-card">
                <div class="output-header"><h4>Inventory Status</h4></div>
                <div style="padding: 24px; text-align: center; color: #6d7175;">
                    No inventory items found
                </div>
            </div>
            """

        return {"success": True, "html": html}

    except Exception as e:
        logger.error(f"Error updating inventory: {e}")
        return {"success": False, "error": str(e)}
