from flask import Blueprint, render_template_string, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, ShopifyStore
from access_control import require_access
from input_validation import validate_url, sanitize_input

shopify_bp = Blueprint('shopify', __name__)

SETTINGS_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Settings - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #fafafa;
            color: #171717;
            -webkit-font-smoothing: antialiased;
        }
        .header {
            background: #fff;
            border-bottom: 1px solid #e5e5e5;
        }
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
            height: 64px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo {
            font-size: 18px;
            font-weight: 600;
            color: #171717;
            text-decoration: none;
        }
        .nav-btn {
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            color: #525252;
        }
        .nav-btn:hover {
            background: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 48px 24px;
        }
        .page-title {
            font-size: 32px;
            font-weight: 700;
            color: #171717;
            margin-bottom: 8px;
        }
        .page-subtitle {
            font-size: 16px;
            color: #737373;
            margin-bottom: 32px;
        }
        .card {
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 12px;
            padding: 32px;
            margin-bottom: 24px;
        }
        .card-header {
            margin-bottom: 20px;
        }
        .card-title {
            font-size: 18px;
            font-weight: 600;
            color: #171717;
            margin-bottom: 4px;
        }
        .card-subtitle {
            font-size: 14px;
            color: #737373;
        }
        .status-connected {
            display: inline-block;
            padding: 6px 12px;
            background: #dcfce7;
            color: #166534;
            border-radius: 12px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 12px;
        }
        .info-grid {
            display: grid;
            gap: 12px;
            margin: 20px 0;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #f5f5f5;
            font-size: 14px;
        }
        .info-row:last-child {
            border-bottom: none;
        }
        .info-label {
            color: #737373;
            font-weight: 500;
        }
        .info-value {
            color: #171717;
            font-weight: 500;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-label {
            display: block;
            font-size: 14px;
            font-weight: 500;
            color: #171717;
            margin-bottom: 8px;
        }
        .form-input {
            width: 100%;
            padding: 12px;
            border: 1px solid #e5e5e5;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
        }
        .form-input:focus {
            outline: none;
            border-color: #171717;
        }
        .form-help {
            font-size: 13px;
            color: #737373;
            margin-top: 6px;
        }
        .btn {
            padding: 12px 20px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary {
            background: #171717;
            color: #fff;
        }
        .btn-primary:hover {
            background: #262626;
        }
        .btn-danger {
            background: #dc2626;
            color: #fff;
        }
        .btn-danger:hover {
            background: #b91c1c;
        }
        .banner-success {
            background: #f0fdf4;
            border: 1px solid #86efac;
            border-left: 3px solid #16a34a;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
            color: #166534;
        }
        .banner-error {
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-left: 3px solid #dc2626;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
            color: #991b1b;
        }
        
        /* Mobile Responsive */
        @media (max-width: 768px) {
            .container { padding: 32px 16px; }
            .page-title { font-size: 26px; }
            .page-subtitle { font-size: 15px; }
            .card { padding: 24px; }
            .card-title { font-size: 16px; }
            .header-content { padding: 0 16px; }
            .nav-btn { padding: 6px 10px; font-size: 13px; }
            .info-row { flex-direction: column; gap: 4px; }
        }
        @media (max-width: 480px) {
            .page-title { font-size: 24px; }
            .card { padding: 20px; }
            .btn { padding: 10px 16px; font-size: 13px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <a href="/dashboard" class="logo">Employee Suite v1</a>
            <a href="/dashboard" class="nav-btn">Back to Dashboard</a>
        </div>
    </div>
    
    <div class="container">
        <h1 class="page-title">Settings</h1>
        <p class="page-subtitle">Manage your Shopify connection and account</p>
        
        {% if success %}
        <div class="banner-success">{{ success }}</div>
        {% endif %}
        
        {% if error %}
        <div class="banner-error">{{ error }}</div>
        {% endif %}
        
        {% if current_user.is_subscribed %}
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Subscription</h2>
                <p class="card-subtitle">Manage your subscription</p>
            </div>
            <div class="info-grid">
                <div class="info-row">
                    <span class="info-label">Status</span>
                    <span class="info-value">Active</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Plan</span>
                    <span class="info-value">Employee Suite Pro</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Billing</span>
                    <span class="info-value">$500/month</span>
                </div>
            </div>
            <form method="POST" action="{{ url_for('shopify.cancel_subscription') }}" style="margin-top: 20px;">
                <button type="submit" class="btn btn-danger" onclick="return confirm('Cancel subscription? You will lose access to all features.')">Cancel Subscription</button>
            </form>
        </div>
        {% endif %}
        
        {% if store %}
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Shopify Connection</h2>
                <span class="status-connected">✓ Connected</span>
            </div>
            <div class="info-grid">
                <div class="info-row">
                    <span class="info-label">Store URL</span>
                    <span class="info-value">{{ store.shop_url }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Connected</span>
                    <span class="info-value">{{ store.created_at.strftime('%B %d, %Y') }}</span>
                </div>
            </div>
            <form method="POST" action="{{ url_for('shopify.disconnect_store') }}" style="margin-top: 20px;">
                <button type="submit" class="btn btn-danger" onclick="return confirm('Disconnect store?')">Disconnect Store</button>
            </form>
        </div>
        {% else %}
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Connect Shopify Store</h2>
                <p class="card-subtitle">Connect your store to start automating</p>
            </div>
            <form method="POST" action="{{ url_for('shopify.connect_store') }}">
                <div class="form-group">
                    <label class="form-label">Store URL</label>
                    <input type="text" name="shop_url" placeholder="yourstore.myshopify.com" class="form-input" required>
                    <p class="form-help">Your Shopify store URL</p>
                </div>
                <div class="form-group">
                    <label class="form-label">Admin API Access Token</label>
                    <input type="password" name="access_token" class="form-input" required>
                    <p class="form-help">Get this from Shopify Admin → Settings → Apps → Develop apps</p>
                </div>
                <button type="submit" class="btn btn-primary">Connect Store</button>
            </form>
        </div>
        {% endif %}
    </div>
</body>
</html>
'''

@shopify_bp.route('/settings/shopify')
@login_required
@require_access
def shopify_settings():
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    return render_template_string(SETTINGS_HTML, store=store, success=request.args.get('success'), error=request.args.get('error'))

@shopify_bp.route('/settings/shopify/connect', methods=['POST'])
@login_required
def connect_store():
    shop_url = request.form.get('shop_url', '').strip()
    access_token = request.form.get('access_token', '').strip()
    
    # Input validation
    if not shop_url or not access_token:
        return redirect(url_for('shopify.shopify_settings', error='Store URL and access token are required.'))
    
    # Sanitize and validate shop URL
    shop_url = sanitize_input(shop_url)
    # Remove https:// or http:// if present
    shop_url = shop_url.replace('https://', '').replace('http://', '').replace('www.', '')
    
    # Validate Shopify URL format
    if not validate_url(shop_url):
        return redirect(url_for('shopify.shopify_settings', error='Invalid Shopify store URL format. Use: yourstore.myshopify.com'))
    
    # Validate access token (basic check - should be non-empty)
    if len(access_token) < 10:
        return redirect(url_for('shopify.shopify_settings', error='Invalid access token format.'))
    
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

@shopify_bp.route('/settings/shopify/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel user's Stripe subscription"""
    import stripe
    import os
    
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    
    if not current_user.is_subscribed:
        return redirect(url_for('shopify.shopify_settings', error='No active subscription found.'))
    
    if not current_user.stripe_customer_id:
        return redirect(url_for('shopify.shopify_settings', error='No Stripe customer ID found.'))
    
    try:
        # Get all subscriptions for this customer
        subscriptions = stripe.Subscription.list(
            customer=current_user.stripe_customer_id,
            status='active',
            limit=10
        )
        
        # Cancel all active subscriptions
        cancelled_count = 0
        for subscription in subscriptions.data:
            stripe.Subscription.delete(subscription.id)
            cancelled_count += 1
        
        if cancelled_count == 0:
            return redirect(url_for('shopify.shopify_settings', error='No active subscriptions found in Stripe.'))
        
        # Update database
        current_user.is_subscribed = False
        db.session.commit()
        
        # Send cancellation email
        try:
            from email_service import send_cancellation_email
            send_cancellation_email(current_user.email)
        except Exception as e:
            print(f"Failed to send cancellation email: {e}")
        
        return redirect(url_for('shopify.shopify_settings', success='Subscription cancelled successfully. You will retain access until the end of your billing period.'))
        
    except stripe.error.StripeError as e:
        print(f"Stripe error during cancellation: {e}")
        return redirect(url_for('shopify.shopify_settings', error=f'Failed to cancel subscription: {str(e)}'))
    except Exception as e:
        print(f"Unexpected error during cancellation: {e}")
        return redirect(url_for('shopify.shopify_settings', error='An unexpected error occurred. Please contact support.'))
