from shopify_integration import ShopifyClient
from flask_login import current_user
from models import ShopifyStore

def generate_report():
    try:
        if not current_user.is_authenticated:
            return {
                "products": [],
                "total_revenue": "$0",
                "total_products": 0,
                "error": "Please log in first"
            }
        
        store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
        
        if not store:
            return {
                "products": [],
                "total_revenue": "$0",
                "total_products": 0,
                "error": "No Shopify store connected"
            }
        
        client = ShopifyClient(store.shop_url, store.access_token)
        
        # Get products
        products = client.get_products()
        if isinstance(products, dict) and "error" in products:
            return {
                "products": [],
                "total_revenue": "$0",
                "total_products": 0,
                "error": products["error"]
            }
        
        # Get orders for revenue calculation
        orders = client.get_orders(limit=250)  # Last 250 orders
        if isinstance(orders, dict) and "error" in orders:
            orders = []
        
        # Calculate revenue
        total_revenue = sum(float(order.get('total_price', 0)) for order in orders)
        
        # Format product data
        product_list = []
        for product in products[:10]:  # Top 10 products
            # Calculate revenue for this product from orders
            product_id = str(product.get('id'))
            product_revenue = 0
            
            for order in orders:
                for item in order.get('line_items', []):
                    if str(item.get('product_id')) == product_id:
                        product_revenue += float(item.get('price', 0)) * int(item.get('quantity', 0))
            
            product_list.append({
                "name": product.get('product', 'Unknown'),
                "stock": product.get('stock', 0),
                "revenue": f"${product_revenue:,.2f}"
            })
        
        return {
            "products": product_list,
            "total_revenue": f"${total_revenue:,.2f}",
            "total_products": len(products),
            "total_orders": len(orders)
        }
        
    except Exception as e:
        return {
            "products": [],
            "total_revenue": "$0",
            "total_products": 0,
            "error": str(e)
        }

if __name__ == "__main__":
    result = generate_report()
    print(f"Result: {result}")
