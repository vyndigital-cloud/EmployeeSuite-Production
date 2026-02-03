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
            html = """
            <div style="margin-bottom: 16px;">
                <table class="premium-table">
                    <thead>
                        <tr>
                            <th>Order</th>
                            <th>Status</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for order in orders[:5]:  # Show first 5 for compact view
                # Mock status logic
                try:
                    val = float(order['total'].replace('$','').replace(',',''))
                    status_class = "success" if val > 50 else "warning"
                    status_text = "Paid" if status_class == "success" else "Pending"
                except:
                    status_class = "warning"
                    status_text = "Pending"
                
                html += f"""
                        <tr>
                            <td>
                                <span style="font-weight: 600; color: var(--primary);">#{order['id']}</span>
                                <div style="font-size: 11px; color: var(--text-secondary);">{order['customer']}</div>
                            </td>
                            <td><span class="status-badge {status_class}">{status_text}</span></td>
                            <td style="font-weight: 600;">{order['total']}</td>
                        </tr>
                """
            html += """
                    </tbody>
                </table>
            </div>
            """
        else:
            html = """
            <div class="output-card">
                <div class="output-header"><h4>Recent Orders</h4></div>
                <div style="padding: 24px; text-align: center; color: #6d7175;">
                    No orders found
                </div>
            </div>
            """

        return {"success": True, "html": html}

    except Exception as e:
        logger.error(f"Error processing orders: {e}")
        return {"success": False, "error": str(e)}
