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
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div style="background: var(--slate-50); padding: 16px; border-radius: var(--radius-md); text-align: center;">
                <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Revenue</div>
                <div style="font-size: 20px; font-weight: 700; color: var(--text-primary);">${total_revenue:,.2f}</div>
            </div>
            
            <div style="background: var(--slate-50); padding: 16px; border-radius: var(--radius-md); text-align: center;">
                 <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Orders</div>
                <div style="font-size: 20px; font-weight: 700; color: var(--text-primary);">{len(orders) if orders else 0}</div>
            </div>
            
            <div style="grid-column: span 2; background: var(--slate-50); padding: 16px; border-radius: var(--radius-md); display: flex; justify-content: space-between; align-items: center;">
                 <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">Avg. Order Value</div>
                 <div style="font-size: 16px; font-weight: 700; color: var(--primary);">${avg_value:,.2f}</div>
            </div>
        </div>
        """

        return {"success": True, "html": html}

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return {"success": False, "error": str(e)}
