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
            <div class="inventory-grid">
            """
            for item in inventory[:5]:  # Show first 5
                # Calculate simple percentage
                try:
                    stock_val = int(item['stock'])
                    percentage = min(100, max(0, (stock_val / 50) * 100))
                    # Logic for low stock color
                    is_low = stock_val < 10
                    fill_class = "low" if is_low else ""
                except (ValueError, TypeError):
                    stock_val = 0
                    percentage = 0
                    fill_class = "low"
                
                html += f"""
                    <div class="inventory-item">
                        <div style="flex: 1;">
                            <div style="font-weight: 500; color: var(--text-primary);">{item['product']}</div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">{item['price']}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 12px; font-weight: 600; margin-bottom: 4px;">{stock_val} units</div>
                            <div class="stock-bar">
                                <div class="stock-fill {fill_class}" style="width: {percentage}%"></div>
                            </div>
                        </div>
                    </div>
                """
            html += """
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
