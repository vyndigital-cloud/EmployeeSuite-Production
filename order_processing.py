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
            <div class="output-card">
                <div class="output-header">
                    <h4>Recent Orders</h4>
                </div>
                <div class="table-responsive">
                    <table class="premium-table">
                        <thead>
                            <tr>
                                <th>Order</th>
                                <th>Customer</th>
                                <th>Status</th>
                                <th>Total</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            for order in orders[:10]:  # Show first 10
                # Mock status for UI demo since API doesn't return it yet
                status_class = "status-paid" if float(order['total'].replace('$','').replace(',','')) > 50 else "status-pending"
                status_text = "Paid" if status_class == "status-paid" else "Pending"
                
                html += f"""
                            <tr>
                                <td><a href="#" class="order-link">#{order['id']}</a></td>
                                <td>{order['customer']}</td>
                                <td><span class="status-pill {status_class}">{status_text}</span></td>
                                <td>{order['total']}</td>
                            </tr>
                """
            html += """
                        </tbody>
                    </table>
                </div>
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
