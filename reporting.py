from flask_login import current_user
from models import ShopifyStore
from shopify_integration import ShopifyClient

def generate_report():
    """Generate revenue report from Shopify data"""
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    
    if not store:
        return {"error": "No Shopify store connected"}
    
    try:
        client = ShopifyClient(store.shop_url, store.access_token)
        
        # Get raw Shopify data
        orders_data = client._make_request("orders.json")
        products_data = client._make_request("products.json")
        
        if "error" in orders_data:
            return {"error": orders_data["error"]}
        if "error" in products_data:
            return {"error": products_data["error"]}
        
        orders = orders_data.get('orders', [])
        products_raw = products_data.get('products', [])
        
        # Calculate revenue
        total_revenue = sum(float(order.get('total_price', 0)) for order in orders)
        order_count = len(orders)
        
        # Build product revenue map
        product_revenue = {}
        for order in orders:
            for item in order.get('line_items', []):
                product_id = item.get('product_id')
                revenue = float(item.get('price', 0)) * int(item.get('quantity', 0))
                product_revenue[product_id] = product_revenue.get(product_id, 0) + revenue
        
        # Build top products list
        top_products = []
        for product in products_raw:
            product_id = product.get('id')
            total_inventory = sum(v.get('inventory_quantity', 0) for v in product.get('variants', []))
            
            if product_id in product_revenue:
                top_products.append({
                    'title': product.get('title', 'Unknown'),
                    'revenue': product_revenue[product_id],
                    'inventory': total_inventory
                })
        
        top_products.sort(key=lambda x: x['revenue'], reverse=True)
        
        return {
            'total_revenue': total_revenue,
            'order_count': order_count,
            'product_count': len(products_raw),
            'products': top_products,
            'error': None
        }
    
    except Exception as e:
        return {"error": f"Error generating report: {str(e)}"}

def generate_report_html(report):
    """Generate clean HTML for report display"""
    if report.get('error'):
        return f'<div style="color: #dc2626; font-size: 14px; padding: 16px; background: #fef2f2; border-radius: 6px; border-left: 3px solid #dc2626;">{report["error"]}</div>'
    
    products_html = ""
    if report.get('products'):
        products_html = "<div style='margin: 20px 0;'>"
        products_html += "<h4 style='font-size: 15px; font-weight: 600; color: #171717; margin-bottom: 16px;'>Top Products</h4>"
        for p in report['products'][:10]:
            products_html += f"""
            <div style='display: flex; justify-content: space-between; padding: 14px; margin: 8px 0; background: #fafafa; border-radius: 6px; border-left: 3px solid #e5e5e5;'>
                <div>
                    <div style='font-weight: 500; color: #171717; font-size: 14px;'>{p['title']}</div>
                    <div style='color: #737373; margin-top: 4px; font-size: 13px;'>Stock: {p['inventory']} units</div>
                </div>
                <div style='font-weight: 600; color: #171717; font-size: 16px;'>${p['revenue']:.2f}</div>
            </div>
            """
        products_html += "</div>"
    
    summary_html = f"""
    <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-top: 24px;'>
        <div style='background: #fafafa; padding: 16px; border-radius: 8px; border: 1px solid #e5e5e5;'>
            <div style='font-size: 12px; color: #737373; font-weight: 600; margin-bottom: 8px; letter-spacing: 0.5px;'>TOTAL REVENUE</div>
            <div style='font-size: 22px; font-weight: 700; color: #171717;'>${report.get('total_revenue', 0):.2f}</div>
        </div>
        <div style='background: #fafafa; padding: 16px; border-radius: 8px; border: 1px solid #e5e5e5;'>
            <div style='font-size: 12px; color: #737373; font-weight: 600; margin-bottom: 8px; letter-spacing: 0.5px;'>PRODUCTS</div>
            <div style='font-size: 22px; font-weight: 700; color: #171717;'>{report.get('product_count', 0)}</div>
        </div>
        <div style='background: #fafafa; padding: 16px; border-radius: 8px; border: 1px solid #e5e5e5;'>
            <div style='font-size: 12px; color: #737373; font-weight: 600; margin-bottom: 8px; letter-spacing: 0.5px;'>ORDERS</div>
            <div style='font-size: 22px; font-weight: 700; color: #171717;'>{report.get('order_count', 0)}</div>
        </div>
    </div>
    """
    
    return products_html + summary_html
