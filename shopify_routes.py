from flask import Blueprint, render_template_string, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, ShopifyStore

shopify_bp = Blueprint('shopify', __name__)

SETTINGS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Shopify Settings - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; background: white; padding: 20px 30px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header h1 { color: #667eea; }
        .back-btn { background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; text-decoration: none; }
        .card { background: white; border-radius: 15px; padding: 30px; margin: 20px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; color: #333; font-weight: 500; }
        input { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 16px; }
        input:focus { outline: none; border-color: #667eea; }
        .btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 14px 30px; border-radius: 8px; font-size: 16px; cursor: pointer; font-weight: 600; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        .btn-danger { background: #dc3545; }
        .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .error { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .store-info { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .store-info h3 { color: #28a745; margin-bottom: 10px; }
        .help-text { font-size: 14px; color: #666; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚙️ Shopify Settings</h1>
            <a href="{{ url_for('dashboard') }}" class="back-btn">← Back to Dashboard</a>
        </div>
        
        {% if success %}
        <div class="success">{{ success }}</div>
        {% endif %}
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        {% if store %}
        <div class="card">
            <div class="store-info">
                <h3>✅ Connected Store</h3>
                <p><strong>Store URL:</strong> {{ store.shop_url }}</p>
                <p><strong>Connected:</strong> {{ store.created_at.strftime('%B %d, %Y') }}</p>
                <p><strong>Status:</strong> {% if store.is_active %}Active{% else %}Inactive{% endif %}</p>
            </div>
            <form method="POST" action="{{ url_for('shopify.disconnect_store') }}">
                <button type="submit" class="btn btn-danger" onclick="return confirm('Are you sure you want to disconnect this store?')">Disconnect Store</button>
            </form>
        </div>
        {% else %}
        <div class="card">
            <h2>Connect Your Shopify Store</h2>
            <p style="margin: 20px 0; color: #666;">Connect your Shopify store to start automating your inventory and orders.</p>
            
            <form method="POST" action="{{ url_for('shopify.connect_store') }}">
                <div class="form-group">
                    <label>Store URL</label>
                    <input type="text" name="shop_url" placeholder="your-store.myshopify.com" required>
                    <p class="help-text">Your Shopify store URL (e.g., my-store.myshopify.com)</p>
                </div>
                
                <div class="form-group">
                    <label>Admin API Access Token</label>
                    <input type="text" name="access_token" placeholder="shpat_xxxxx" required>
                    <p class="help-text">Get this from your Shopify Admin → Apps → Develop apps</p>
                </div>
                
                <button type="submit" class="btn">Connect Store</button>
            </form>
            
            <div style="margin-top: 30px; padding: 20px; background: #fff3cd; border-radius: 8px;">
                <h4>📚 How to get your API token:</h4>
                <ol style="margin: 10px 0 0 20px; line-height: 1.8;">
                    <li>Go to your Shopify Admin</li>
                    <li>Settings → Apps and sales channels</li>
                    <li>Develop apps → Create an app</li>
                    <li>Configure Admin API scopes (enable: read_products, write_products, read_inventory, write_inventory, read_orders)</li>
                    <li>Install app → Copy the Admin API access token</li>
                </ol>
            </div>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@shopify_bp.route('/settings/shopify')
@login_required
def shopify_settings():
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    return render_template_string(SETTINGS_HTML, store=store, success=request.args.get('success'), error=request.args.get('error'))

@shopify_bp.route('/settings/shopify/connect', methods=['POST'])
@login_required
def connect_store():
    shop_url = request.form.get('shop_url')
    access_token = request.form.get('access_token')
    
    if ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first():
        return redirect(url_for('shopify.shopify_settings', error='You already have a connected store. Disconnect it first.'))
    
    new_store = ShopifyStore(
        user_id=current_user.id,
        shop_url=shop_url,
        access_token=access_token,
        is_active=True
    )
    
    db.session.add(new_store)
    db.session.commit()
    
    return redirect(url_for('shopify.shopify_settings', success='Store connected successfully!'))

@shopify_bp.route('/settings/shopify/disconnect', methods=['POST'])
@login_required
def disconnect_store():
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    if store:
        store.is_active = False
        db.session.commit()
        return redirect(url_for('shopify.shopify_settings', success='Store disconnected successfully!'))
    return redirect(url_for('shopify.shopify_settings', error='No active store found.'))
