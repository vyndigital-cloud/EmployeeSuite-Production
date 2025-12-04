from flask import Blueprint, render_template_string, request, redirect, url_for, session
from flask_login import login_required, current_user
import stripe
import os
from models import db
from datetime import datetime
from email_service import send_payment_success

billing_bp = Blueprint('billing', __name__)

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

SUBSCRIBE_HTML = '''
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
        }
        .header { background: #fff; border-bottom: 1px solid #e5e5e5; }
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
            height: 64px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo { font-size: 18px; font-weight: 600; color: #171717; text-decoration: none; }
        .nav-btn { padding: 8px 14px; border-radius: 6px; font-size: 14px; font-weight: 500; text-decoration: none; color: #525252; }
        .nav-btn:hover { background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; padding: 48px 24px; }
        .page-title { font-size: 32px; font-weight: 700; color: #171717; margin-bottom: 8px; }
        .page-subtitle { font-size: 16px; color: #737373; margin-bottom: 32px; }
        .pricing-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 32px; }
        .pricing-item {
            padding: 20px 0;
            border-bottom: 1px solid #f5f5f5;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .pricing-item:last-child { border-bottom: none; }
        .pricing-label { font-size: 16px; font-weight: 500; color: #171717; }
        .pricing-detail { font-size: 13px; color: #737373; margin-top: 4px; }
        .pricing-value { font-size: 24px; font-weight: 700; color: #171717; }
        .features-list { list-style: none; margin: 24px 0; padding: 24px 0; border-top: 1px solid #f5f5f5; }
        .features-list li {
            padding: 10px 0;
            font-size: 14px;
            color: #525252;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .features-list li:before { content: '✓'; color: #16a34a; font-weight: 700; font-size: 16px; }
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
        }
        .btn:hover { background: #3a5c2a; }
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
        <h1 class="page-title" style="color: #4a7338;">Ready to Subscribe?</h1>
        <p class="page-subtitle">Your free trial is active. Subscribe now to ensure uninterrupted access when your trial ends.</p>
        
        <div class="pricing-card">
            <div class="pricing-item">
                <div>
                    <div class="pricing-label">Setup Fee</div>
                    <div class="pricing-detail">One-time payment</div>
                </div>
                <div class="pricing-value">$1,000</div>
            </div>
            
            <div class="pricing-item">
                <div>
                    <div class="pricing-label">Monthly Subscription</div>
                    <div class="pricing-detail">Recurring monthly payment</div>
                </div>
                <div class="pricing-value">$500/mo</div>
            </div>
            
            <ul class="features-list">
                <li>Real-time inventory monitoring</li>
                <li>Low-stock alerts (set your own threshold)</li>
                <li>Order tracking and status updates</li>
                <li>Revenue reports by product</li>
                <li>Shopify API integration</li>
                <li>Email support</li>
            </ul>
            
            <form method="POST" action="{{ url_for('billing.create_checkout') }}">
                <button type="submit" class="btn">Subscribe Now</button>
            </form>
        </div>
    </div>
</body>
</html>
'''

SUCCESS_HTML = '''
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
        .success-container { text-align: center; max-width: 480px; }
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
        .success-title { font-size: 28px; font-weight: 700; color: #171717; margin-bottom: 12px; }
        .success-text { font-size: 16px; color: #737373; line-height: 1.6; margin-bottom: 24px; }
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
        .btn:hover { background: #3a5c2a; }
    </style>
</head>
<body>
    <div class="success-container">
        <div class="success-icon">✓</div>
        <h1 class="success-title">🎉 You're All Set!</h1>
        <p class="success-text">Payment confirmed. You now have unlimited access to Employee Suite.</p>
        <a href="{{ url_for('dashboard') }}" class="btn">Go to Dashboard</a>
    </div>
</body>
</html>
'''

@billing_bp.route('/subscribe')
@login_required
def subscribe():
    return render_template_string(SUBSCRIBE_HTML)

@billing_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout():
    try:
        if current_user.is_subscribed:
            return redirect(url_for('dashboard'))
        
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': os.getenv('STRIPE_SETUP_PRICE_ID'), 
                    'quantity': 1,
                },
                {
                    'price': os.getenv('STRIPE_MONTHLY_PRICE_ID'), 
                    'quantity': 1,
                }
            ],
            mode='subscription',
            subscription_data={
                'description': 'Employee Suite - Shopify Inventory Automation'
            },
            success_url=url_for('billing.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('billing.subscribe', _external=True),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return f"Error: {str(e)}", 500

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
            
            # Send confirmation email
            try:
                send_payment_success(current_user.email)
            except:
                pass
        except:
            pass
    return render_template_string(SUCCESS_HTML)
