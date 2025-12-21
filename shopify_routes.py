from flask import Blueprint, render_template_string, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, ShopifyStore
from access_control import require_access
from input_validation import validate_url, sanitize_input
from session_token_verification import verify_session_token
from logging_config import logger

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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f6f6f7;
            color: #202223;
            -webkit-font-smoothing: antialiased;
            line-height: 1.5;
        }
        .header {
            background: #ffffff;
            border-bottom: 1px solid #e1e3e5;
            position: sticky;
            top: 0;
            z-index: 100;
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
            font-size: 16px;
            font-weight: 600;
            color: #202223;
            text-decoration: none;
            letter-spacing: -0.2px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .nav-btn {
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            color: #6d7175;
            transition: background 0.15s;
        }
        .nav-btn:hover {
            background: #f6f6f7;
            color: #202223;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 32px 24px;
        }
        .page-title {
            font-size: 28px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 8px;
            letter-spacing: -0.3px;
        }
        .page-subtitle {
            font-size: 15px;
            color: #6d7175;
            margin-bottom: 32px;
        }
        .card {
            background: #ffffff;
            border: 1px solid #e1e3e5;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 20px;
        }
        .card-header {
            margin-bottom: 20px;
        }
        .card-title {
            font-size: 17px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 4px;
        }
        .card-subtitle {
            font-size: 14px;
            color: #6d7175;
        }
        .status-connected {
            display: inline-block;
            padding: 6px 12px;
            background: #e3fcef;
            color: #008060;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 16px;
        }
        .info-grid {
            display: grid;
            gap: 16px;
            margin: 20px 0;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 16px 0;
            border-bottom: 1px solid #e1e3e5;
            font-size: 14px;
        }
        .info-row:last-child {
            border-bottom: none;
        }
        .info-label {
            color: #6d7175;
            font-weight: 400;
        }
        .info-value {
            color: #202223;
            font-weight: 500;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-label {
            display: block;
            font-size: 13px;
            font-weight: 500;
            color: #202223;
            margin-bottom: 6px;
        }
        .form-input {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #e1e3e5;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
            background: #ffffff;
            transition: border-color 0.15s;
        }
        .form-input:focus {
            outline: none;
            border-color: #008060;
            box-shadow: 0 0 0 1px #008060;
        }
        .form-help {
            font-size: 13px;
            color: #6d7175;
            margin-top: 6px;
        }
        .btn {
            padding: 10px 16px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: background 0.15s;
        }
        .btn-primary {
            background: #008060;
            color: #fff;
        }
        .btn-primary:hover {
            background: #006e52;
        }
        .btn-danger {
            background: #d72c0d;
            color: #fff;
        }
        .btn-danger:hover {
            background: #bf280a;
        }
        .banner-success {
            background: #e3fcef;
            border: 1px solid #b2f5d1;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
            color: #008060;
            font-weight: 400;
        }
        .banner-error {
            background: #fff4f4;
            border: 1px solid #fecaca;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
            color: #d72c0d;
            font-weight: 400;
        }
        
        /* Mobile */
        @media (max-width: 768px) {
            .container { padding: 24px 16px; }
            .page-title { font-size: 24px; }
            .card { padding: 20px; }
            .header-content { padding: 0 16px; height: 56px; }
            .info-row { flex-direction: column; gap: 4px; }
        }
        @media (max-width: 480px) {
            .container { padding: 20px 12px; }
            .page-title { font-size: 20px; }
            .card { padding: 16px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <a href="/dashboard" style="text-decoration: none; color: inherit; display: flex; align-items: center; gap: 10px; font-weight: 600;" class="logo">
                <span>Employee Suite</span>
            </a>
            <a href="/dashboard" class="nav-btn">Back to Dashboard</a>
        </div>
    </div>
    
    <div class="container">
        <h1 class="page-title">Settings</h1>
        <p class="page-subtitle">Manage your Shopify connection and account</p>
        
        {% if success %}
        <div class="banner-success" style="animation: fadeIn 0.5s ease-in;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 24px;">🎉</span>
                <div>
                    <strong style="display: block; margin-bottom: 4px;">{{ success }}</strong>
                    <span style="font-size: 14px; opacity: 0.9;">You're all set! Head back to the dashboard to start monitoring your store.</span>
                </div>
            </div>
        </div>
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
                    <span class="info-value">$29/month</span>
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
                <p class="card-subtitle">Connect your store to start monitoring your operations</p>
            </div>
            
            <!-- OAuth Quick Connect (1-2 clicks) -->
            <div style="margin-bottom: 24px; padding: 24px; background: #fafafa; border: 1px solid #e5e5e5; border-radius: 16px;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                    <span style="font-size: 24px;">✨</span>
                    <h3 style="font-size: 18px; font-weight: 600; color: #171717; margin: 0;">Quick Connect (Recommended)</h3>
                </div>
                <p style="font-size: 14px; color: #525252; margin-bottom: 20px; line-height: 1.6;">Connect your store in seconds with one click. No need to copy tokens manually. We'll redirect you to Shopify to authorize the connection.</p>
                <div>
                    <label for="shop_oauth" style="display: block; font-size: 14px; font-weight: 500; color: #171717; margin-bottom: 8px;">Enter your store domain</label>
                    <form method="GET" action="/install" style="display: flex; gap: 12px; align-items: flex-start; flex-wrap: wrap;">
                        <div style="flex: 1; min-width: 250px;">
                            <input type="text" id="shop_oauth" name="shop" class="form-input" placeholder="yourstore.myshopify.com" required style="width: 100%; font-size: 15px; padding: 12px;">
                            <p style="font-size: 12px; color: #737373; margin-top: 6px;">Enter your store domain (e.g., mystore.myshopify.com)</p>
                        </div>
                        <div style="display: flex; align-items: flex-start;">
                            <button type="submit" class="btn btn-primary" style="white-space: nowrap; padding: 12px 24px; font-size: 15px; font-weight: 600; background: #0ea5e9; border: none; height: 44px;">Connect with Shopify</button>
                        </div>
                    </form>
                </div>
                <div style="margin-top: 16px; padding: 12px; background: rgba(255,255,255,0.7); border-radius: 8px;">
                    <p style="font-size: 13px; color: #166534; margin: 0; display: flex; align-items: center; gap: 8px;">
                        <span>✓</span>
                        <span>Secure OAuth connection. You'll be redirected to Shopify to approve access.</span>
                    </p>
                </div>
            </div>
            
            <!-- Manual Connection (Advanced/Fallback) -->
            <details style="margin-top: 24px;">
                <summary style="font-size: 14px; font-weight: 500; color: #525252; cursor: pointer; padding: 14px; background: #fafafa; border-radius: 8px; border: 1px solid #e5e5e5; user-select: none;">
                    🔧 Advanced: Connect with Access Token (Manual Method)
                </summary>
                <div style="margin-top: 20px; padding: 20px; background: #fafafa; border-radius: 8px; border: 1px solid #e5e5e5;">
                    <p style="font-size: 13px; color: #737373; margin-bottom: 20px; line-height: 1.6;">
                        <strong>When to use this:</strong> Only if you need to connect a development store, custom app, or if the Quick Connect above doesn't work for your setup.
                    </p>
                    <form method="POST" action="{{ url_for('shopify.connect_store') }}">
                        <div class="form-group">
                            <label class="form-label">Store URL</label>
                            <input type="text" name="shop_url" placeholder="yourstore.myshopify.com" class="form-input" required>
                            <p class="form-help">Your Shopify store URL</p>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Admin API Access Token</label>
                            <input type="password" name="access_token" class="form-input" placeholder="shpat_xxxxxxxxxxxx" required>
                            <p class="form-help">Get this from: <strong>Shopify Admin → Settings → Apps and sales channels → Develop apps → Create app → Admin API access token</strong></p>
                        </div>
                        <button type="submit" class="btn btn-primary" style="background: #0ea5e9;">Connect Store</button>
                    </form>
                </div>
            </details>
        </div>
        {% endif %}
    </div>
</body>
</html>
'''

@shopify_bp.route('/settings/shopify')
@verify_session_token
@login_required
@require_access
def shopify_settings():
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    return render_template_string(SETTINGS_HTML, store=store, success=request.args.get('success'), error=request.args.get('error'))

@shopify_bp.route('/settings/shopify/connect', methods=['POST'])
@verify_session_token
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
            logger.error(f"Failed to send cancellation email: {e}")
        
        return redirect(url_for('shopify.shopify_settings', success='Subscription cancelled successfully. You will retain access until the end of your billing period.'))
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error during cancellation: {e}")
        return redirect(url_for('shopify.shopify_settings', error=f'Failed to cancel subscription: {str(e)}'))
    except Exception as e:
        logger.error(f"Unexpected error during cancellation: {e}")
        return redirect(url_for('shopify.shopify_settings', error='An unexpected error occurred. Please contact support.'))
