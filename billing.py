from flask import Blueprint, render_template_string, request, redirect, url_for
from flask_login import login_required, current_user
from models import db
import stripe
import os
from datetime import datetime

billing_bp = Blueprint('billing', __name__)
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

CHECKOUT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Subscribe - Employee Suite</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
        .container { background: white; border-radius: 15px; padding: 40px; max-width: 500px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        h1 { color: #667eea; margin-bottom: 20px; text-align: center; }
        .trial-banner { background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; color: #856404; }
        .trial-banner strong { color: #d63384; }
        .pricing { margin: 30px 0; }
        .price-item { padding: 15px; background: #f8f9fa; border-radius: 8px; margin: 10px 0; }
        .price-item .label { color: #666; font-size: 14px; }
        .price-item .amount { font-size: 2em; color: #667eea; font-weight: bold; }
        .total { font-size: 1.5em; color: #333; margin: 20px 0; padding: 20px; background: #d4edda; border-radius: 8px; text-align: center; }
        .features { list-style: none; margin: 30px 0; }
        .features li { padding: 10px 0; color: #666; }
        .features li:before { content: "✅ "; }
        .btn { width: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 16px; border-radius: 8px; font-size: 18px; cursor: pointer; font-weight: 600; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Employee Suite Pro</h1>
        
        {% if trial_active %}
        <div class="trial-banner">
            ⏰ Your free trial ends in <strong>{{ days_left }} days</strong><br>
            Subscribe now to continue without interruption!
        </div>
        {% endif %}
        
        <div class="pricing">
            <div class="price-item">
                <div class="label">Setup Fee (One-time)</div>
                <div class="amount">$1,000 AUD</div>
            </div>
            <div class="price-item">
                <div class="label">Monthly Subscription</div>
                <div class="amount">$500 AUD</div>
            </div>
        </div>
        <div class="total">
            💳 First payment: $1,500 AUD<br>
            <small style="color: #666;">Then $500 AUD/month</small>
        </div>
        <ul class="features">
            <li>Unlimited Shopify orders</li>
            <li>Real-time inventory sync</li>
            <li>Multi-platform support</li>
            <li>Automated reporting</li>
            <li>White-glove onboarding ($1000 value)</li>
            <li>Priority 24/7 support</li>
        </ul>
        <form method="POST" action="{{ url_for('billing.create_checkout') }}">
            <button type="submit" class="btn">Subscribe Now - $1,500 AUD</button>
        </form>
    </div>
</body>
</html>
"""

@billing_bp.route('/subscribe')
@login_required
def subscribe():
    trial_active = current_user.is_trial_active()
    days_left = (current_user.trial_ends_at - datetime.utcnow()).days if trial_active else 0
    return render_template_string(CHECKOUT_HTML, trial_active=trial_active, days_left=days_left)

@billing_bp.route('/create-checkout', methods=['POST'])
@login_required
def create_checkout():
    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[
                {'price': os.getenv('STRIPE_SETUP_PRICE_ID'), 'quantity': 1},
                {'price': os.getenv('STRIPE_MONTHLY_PRICE_ID'), 'quantity': 1}
            ],
            mode='subscription',
            success_url=url_for('billing.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('billing.subscribe', _external=True),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return str(e), 400

@billing_bp.route('/success')
@login_required
def success():
    session_id = request.args.get('session_id')
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            current_user.stripe_customer_id = session.customer
            current_user.is_subscribed = True
            db.session.commit()
        except:
            pass
    
    return render_template_string("""
    <html>
    <head>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
            .container { background: white; border-radius: 15px; padding: 60px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.3); max-width: 600px; }
            h1 { color: #28a745; font-size: 3em; margin-bottom: 20px; }
            p { color: #666; font-size: 1.2em; margin-bottom: 30px; line-height: 1.6; }
            .btn { background: #667eea; color: white; padding: 14px 30px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎉 Welcome to Employee Suite Pro!</h1>
            <p><strong>Your subscription is now active.</strong></p>
            <p>Setup fee: $1,000 AUD paid ✅<br>Monthly billing: $500 AUD/month</p>
            <p>Check your email for onboarding details.</p>
            <a href="{{ url_for('dashboard') }}" class="btn">Go to Dashboard →</a>
        </div>
    </body>
    </html>
    """)
SUBSCRIBE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Subscribe - Employee Suite</title>
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
            max-width: 600px;
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
        .pricing-card {
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 12px;
            padding: 32px;
            margin-bottom: 24px;
        }
        .price {
            font-size: 48px;
            font-weight: 700;
            color: #171717;
            margin-bottom: 8px;
        }
        .price-currency {
            font-size: 24px;
            color: #737373;
        }
        .price-period {
            font-size: 16px;
            color: #737373;
        }
        .price-note {
            font-size: 14px;
            color: #737373;
            margin-bottom: 24px;
        }
        .features-list {
            list-style: none;
            margin: 24px 0;
        }
        .features-list li {
            padding: 12px 0;
            font-size: 14px;
            color: #525252;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .features-list li:before {
            content: '✓';
            color: #16a34a;
            font-weight: 700;
            font-size: 16px;
        }
        .btn {
            width: 100%;
            padding: 14px;
            background: #171717;
            color: #fff;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            display: block;
            text-align: center;
        }
        .btn:hover {
            background: #262626;
        }
        .trial-note {
            text-align: center;
            margin-top: 16px;
            font-size: 13px;
            color: #737373;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <a href="/dashboard" class="logo">Employee Suite</a>
            <a href="/dashboard" class="nav-btn">Back to Dashboard</a>
        </div>
    </div>
    
    <div class="container">
        <h1 class="page-title">Subscribe</h1>
        <p class="page-subtitle">Get full access to Employee Suite</p>
        
        <div class="pricing-card">
            <div class="price">
                <span class="price-currency">$1,000</span> setup
            </div>
            <p class="price-note">One-time setup fee</p>
            
            <div class="price">
                <span class="price-currency">$500</span>
                <span class="price-period">/month</span>
            </div>
            <p class="price-note">Billed monthly, cancel anytime</p>
            
            <ul class="features-list">
                <li>Real-time inventory tracking</li>
                <li>Automated low-stock alerts</li>
                <li>Order processing automation</li>
                <li>Revenue analytics & reports</li>
                <li>Multi-store support</li>
                <li>Priority customer support</li>
            </ul>
            
            <form method="POST" action="{{ url_for('billing.create_checkout') }}">
                <button type="submit" class="btn">Subscribe Now</button>
            </form>
            <p class="trial-note">2-day free trial • Cancel anytime</p>
        </div>
    </div>
</body>
</html>
"""
<!DOCTYPE html>
<html>
<head>
    <title>Subscribe - Employee Suite</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
        .container { background: white; border-radius: 15px; padding: 40px; max-width: 500px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        h1 { color: #667eea; margin-bottom: 20px; text-align: center; }
        .trial-banner { background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; color: #856404; }
        .trial-banner strong { color: #d63384; }
        .pricing { margin: 30px 0; }
        .price-item { padding: 15px; background: #f8f9fa; border-radius: 8px; margin: 10px 0; }
        .price-item .label { color: #666; font-size: 14px; }
        .price-item .amount { font-size: 2em; color: #667eea; font-weight: bold; }
        .total { font-size: 1.5em; color: #333; margin: 20px 0; padding: 20px; background: #d4edda; border-radius: 8px; text-align: center; }
        .features { list-style: none; margin: 30px 0; }
        .features li { padding: 10px 0; color: #666; }
        .features li:before { content: "✅ "; }
        .btn { width: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 16px; border-radius: 8px; font-size: 18px; cursor: pointer; font-weight: 600; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Employee Suite Pro</h1>
        
        {% if trial_active %}
        <div class="trial-banner">
            ⏰ Your free trial ends in <strong>{{ days_left }} days</strong><br>
            Subscribe now to continue without interruption!
        </div>
        {% endif %}
        
        <div class="pricing">
            <div class="price-item">
                <div class="label">Setup Fee (One-time)</div>
                <div class="amount">$1,000 AUD</div>
            </div>
            <div class="price-item">
                <div class="label">Monthly Subscription</div>
                <div class="amount">$500 AUD</div>
            </div>
        </div>
        <div class="total">
            💳 First payment: $1,500 AUD<br>
            <small style="color: #666;">Then $500 AUD/month</small>
        </div>
        <ul class="features">
            <li>Unlimited Shopify orders</li>
            <li>Real-time inventory sync</li>
            <li>Multi-platform support</li>
            <li>Automated reporting</li>
            <li>White-glove onboarding ($1000 value)</li>
            <li>Priority 24/7 support</li>
        </ul>
        <form method="POST" action="{{ url_for('billing.create_checkout') }}">
            <button type="submit" class="btn">Subscribe Now - $1,500 AUD</button>
        </form>
    </div>
</body>
</html>
SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Welcome - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="3;url={{ url_for('dashboard') }}">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #fafafa;
            color: #171717;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 24px;
        }
        .success-container {
            text-align: center;
            max-width: 480px;
        }
        .success-icon {
            width: 80px;
            height: 80px;
            background: #dcfce7;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            margin: 0 auto 24px;
        }
        .success-title {
            font-size: 28px;
            font-weight: 700;
            color: #171717;
            margin-bottom: 12px;
        }
        .success-text {
            font-size: 16px;
            color: #737373;
            line-height: 1.6;
            margin-bottom: 24px;
        }
        .btn {
            padding: 12px 24px;
            background: #171717;
            color: #fff;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover {
            background: #262626;
        }
    </style>
</head>
<body>
    <div class="success-container">
        <div class="success-icon">✓</div>
        <h1 class="success-title">Welcome to Employee Suite!</h1>
        <p class="success-text">Your subscription is active. Redirecting to dashboard...</p>
        <a href="{{ url_for('dashboard') }}" class="btn">Go to Dashboard</a>
    </div>
</body>
</html>
"""
<!DOCTYPE html>
<html>
<head>
    <title>Subscribe - Employee Suite</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
        .container { background: white; border-radius: 15px; padding: 40px; max-width: 500px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        h1 { color: #667eea; margin-bottom: 20px; text-align: center; }
        .trial-banner { background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; color: #856404; }
        .trial-banner strong { color: #d63384; }
        .pricing { margin: 30px 0; }
        .price-item { padding: 15px; background: #f8f9fa; border-radius: 8px; margin: 10px 0; }
        .price-item .label { color: #666; font-size: 14px; }
        .price-item .amount { font-size: 2em; color: #667eea; font-weight: bold; }
        .total { font-size: 1.5em; color: #333; margin: 20px 0; padding: 20px; background: #d4edda; border-radius: 8px; text-align: center; }
        .features { list-style: none; margin: 30px 0; }
        .features li { padding: 10px 0; color: #666; }
        .features li:before { content: "✅ "; }
        .btn { width: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 16px; border-radius: 8px; font-size: 18px; cursor: pointer; font-weight: 600; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Employee Suite Pro</h1>
        
        {% if trial_active %}
        <div class="trial-banner">
            ⏰ Your free trial ends in <strong>{{ days_left }} days</strong><br>
            Subscribe now to continue without interruption!
        </div>
        {% endif %}
        
        <div class="pricing">
            <div class="price-item">
                <div class="label">Setup Fee (One-time)</div>
                <div class="amount">$1,000 AUD</div>
            </div>
            <div class="price-item">
                <div class="label">Monthly Subscription</div>
                <div class="amount">$500 AUD</div>
            </div>
        </div>
        <div class="total">
            💳 First payment: $1,500 AUD<br>
            <small style="color: #666;">Then $500 AUD/month</small>
        </div>
        <ul class="features">
            <li>Unlimited Shopify orders</li>
            <li>Real-time inventory sync</li>
            <li>Multi-platform support</li>
            <li>Automated reporting</li>
            <li>White-glove onboarding ($1000 value)</li>
            <li>Priority 24/7 support</li>
        </ul>
        <form method="POST" action="{{ url_for('billing.create_checkout') }}">
            <button type="submit" class="btn">Subscribe Now - $1,500 AUD</button>
        </form>
    </div>
</body>
</html>
