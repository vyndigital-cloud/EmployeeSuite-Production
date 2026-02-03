from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import ShopifyStore, db
from shopify_integration import ShopifyClient
from datetime import datetime, timedelta
import logging

analytics_bp = Blueprint('analytics', __name__)
logger = logging.getLogger(__name__)

@analytics_bp.route('/api/analytics/forecast', methods=['GET'])
@login_required
def get_inventory_forecast():
    """
    PREMIUM FEATURE: Stockout Prediction
    Calculates sales velocity and predicts when items will go out of stock.
    Returns: JSON with 'at_risk_items' and 'total_potential_revenue_loss'
    """
    shop = request.args.get('shop')
    
    # Get store
    if shop:
        store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
    else:
        store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
        
    if not store:
        return jsonify({"error": "Store not found"}), 404
        
    access_token = store.get_access_token()
    if not access_token:
        return jsonify({"error": "Store not connected"}), 401

    try:
        # Use GraphQL to bypass protected customer data restrictions
        from shopify_graphql import ShopifyGraphQLClient
        graphql_client = ShopifyGraphQLClient(store.shop_url, access_token)
        
        # Get products using GraphQL
        products_result = graphql_client.get_all_products()
        
        if isinstance(products_result, dict) and 'error' in products_result:
            return jsonify(products_result), 400

        # 2. Get Recent Sales (Last 30 days) to calculate real Velocity
        from models import Order, OrderItem
        from sqlalchemy import func

        at_risk_items = []
        total_potential_loss = 0.0

        # Value Add: Identify low stock items and project their runout date using real sales data
        today = datetime.utcnow()
        
        # Calculate date range for velocity analysis
        thirty_days_ago = today - timedelta(days=30)
        
        # Convert GraphQL products to expected format
        products = []
        for product_node in products_result:
            # GraphQL returns totalInventory at product level
            total_inventory = product_node.get('totalInventory', 0)
            
            # Get first variant for price (simplified for analytics)
            variants = product_node.get('variants', {}).get('edges', [])
            price = 0
            if variants:
                first_variant = variants[0]['node']
                price = float(first_variant.get('price', 0))
            
            products.append({
                'product': product_node.get('title', 'Unknown'),
                'stock': total_inventory,
                'price': price,
                'variant_title': ''
            })
        
        for p in products:
            stock = p.get('stock', 0)
            if stock > 0 and stock < 20: # Low stock threshold
                
                # Calculate velocity using Shopify API data (no local order storage)
                product_title = p.get('product')
                
                # Get recent orders from Shopify API for velocity calculation
                try:
                    recent_orders = graphql_client.get_orders(limit=250)
                    total_sold = 0
                    
                    # Calculate sales from API data
                    if isinstance(recent_orders, dict) and 'orders' in recent_orders:
                        for order in recent_orders['orders']:
                            order_date = datetime.fromisoformat(order.get('createdAt', '').replace('Z', '+00:00'))
                            if order_date >= thirty_days_ago:
                                for line_item in order.get('lineItems', {}).get('edges', []):
                                    item = line_item['node']
                                    if item.get('title') == product_title:
                                        total_sold += int(item.get('quantity', 0))
                    
                    velocity = total_sold / 30.0  # Daily velocity
                    
                except Exception as api_error:
                    logger.warning(f"Could not fetch order data for velocity: {api_error}")
                    total_sold = 0
                    velocity = max(0.1, stock / 30)  # Conservative fallback estimate
                
                days_remaining = int(stock / velocity) if velocity > 0 else 999
                stockout_date = (today + timedelta(days=days_remaining)).strftime('%Y-%m-%d')
                
                potential_revenue = float(p.get('price', 0)) * stock
                
                if days_remaining < 7:
                    at_risk_items.append({
                        "product_title": product_title,
                        "variant_title": p.get('variant_title', ''),
                        "current_stock": stock,
                        "velocity": f"{velocity:.1f}/day",
                        "days_remaining": days_remaining,
                        "stockout_date": stockout_date,
                        "potential_revenue": potential_revenue,
                        "sales_last_30_days": total_sold
                    })
                    total_potential_loss += (float(p.get('price', 0)) * velocity * 30) # Loss projection
        
        # Sort by urgency
        at_risk_items.sort(key=lambda x: x['days_remaining'])

        return jsonify({
            "success": True,
            "metrics": {
                "at_risk_count": len(at_risk_items),
                "total_potential_loss": total_potential_loss,
                "forecast_period": "7 days"
            },
            "items": at_risk_items[:5] # Top 5 urgent items
        })

    except Exception as e:
        logger.error(f"Analytics Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
