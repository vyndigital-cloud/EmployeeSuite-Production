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
        .logo { font-size: 18px; font-weight: 500; color: #171717; text-decoration: none; }
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
            background: #4a7338;
            color: #fff;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
        }
        .btn:hover { background: #3a5c2a; }
        
        /* Mobile Responsive */
        @media (max-width: 768px) {
            .container { padding: 32px 16px; }
            .page-title { font-size: 26px; }
            .page-subtitle { font-size: 15px; }
            .pricing-card { padding: 24px; }
            .pricing-value { font-size: 20px; }
            .header-content { padding: 0 16px; }
            .logo { font-size: 16px; }
            .nav-btn { padding: 6px 10px; font-size: 13px; }
        }
        @media (max-width: 480px) {
            .page-title { font-size: 24px; }
            .pricing-item { flex-direction: column; align-items: flex-start; gap: 8px; }
            .pricing-value { font-size: 18px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <a href="/dashboard" style="text-decoration: none; color: inherit; display: flex; align-items: center; gap: 10px; font-weight: 600;" class="logo">
                <span style="font-size: 20px;">🚀</span>
                <span>Employee Suite</span>
            </a>
            <a href="/dashboard" class="nav-btn">Back to Dashboard</a>
        </div>
    </div>
    
    <div class="container">
        <h1 class="page-title">{% if not has_access %}Restore Access{% else %}Ready to Subscribe?{% endif %}</h1>
        <p class="page-subtitle">
            {% if not has_access %}
            Your trial has ended. Subscribe now to restore full access to Employee Suite.
            {% elif trial_active and not is_subscribed %}
            Your free trial is active ({{ days_left }} day{{ 's' if days_left != 1 else '' }} remaining). Subscribe now to ensure uninterrupted access when your trial ends.
            {% else %}
            Get unlimited access to all Employee Suite features.
            {% endif %}
        </p>
        
        {% if not has_access %}
        <div style="background: #fef2f2; border-left: 3px solid #dc2626; padding: 16px 20px; border-radius: 8px; margin-bottom: 24px;">
            <p style="color: #991b1b; font-weight: 600; margin: 0;">⚠️ Your access has expired. Subscribe to continue using Employee Suite.</p>
        </div>
        {% elif trial_active and not is_subscribed %}
        <div style="background: #fffbeb; border-left: 3px solid #f59e0b; padding: 16px 20px; border-radius: 8px; margin-bottom: 24px;">
            <p style="color: #92400e; font-weight: 600; margin: 0;">⏰ {{ days_left }} day{{ 's' if days_left != 1 else '' }} left in your trial. Subscribe now to avoid interruption.</p>
        </div>
        {% endif %}
        
        <div class="pricing-card">
            <div style="background: linear-gradient(135deg, #171717 0%, #262626 100%); color: #fff; padding: 24px; border-radius: 12px; margin-bottom: 24px; text-align: center;">
                <div style="font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; opacity: 0.9; margin-bottom: 8px;">Simple Pricing</div>
                <div style="font-size: 48px; font-weight: 700; margin-bottom: 4px;">$29<span style="font-size: 20px; font-weight: 500;">/month</span></div>
                <div style="font-size: 14px; opacity: 0.8;">7-day free trial • No setup fees • Cancel anytime</div>
            </div>
            
            <ul class="features-list">
                <li>Inventory monitoring (updated frequently)</li>
                <li>Low-stock alerts (10 unit threshold)</li>
                <li>Order tracking and status monitoring</li>
                <li>Revenue reports by product</li>
                <li>CSV export for revenue data</li>
                <li>Shopify API integration</li>
                <li>Email support</li>
            </ul>
            
            <form method="POST" action="/create-checkout-session">
                <button type="submit" class="btn">
                    {% if not has_access %}
                    Restore Access Now
                    {% elif trial_active and not is_subscribed %}
                    Subscribe Now ({{ days_left }} day{{ 's' if days_left != 1 else '' }} left)
                    {% else %}
                    Subscribe Now
                    {% endif %}
                </button>
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
            background: #4a7338;
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
    """Subscribe page - shows different messaging based on trial status"""
    trial_active = current_user.is_trial_active()
    has_access = current_user.has_access()
    days_left = (current_user.trial_ends_at - datetime.utcnow()).days if trial_active else 0
    
    return render_template_string(SUBSCRIBE_HTML, 
                                 trial_active=trial_active, 
                                 has_access=has_access,
                                 days_left=days_left,
                                 is_subscribed=current_user.is_subscribed)

@billing_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout():
    """Create Stripe checkout session - optimized for speed"""
    try:
        # Quick check - if already subscribed, redirect immediately
        if current_user.is_subscribed:
            return redirect(url_for('dashboard'))
        
        # Get price ID from env - $29/month plan
        monthly_price_id = os.getenv('STRIPE_MONTHLY_PRICE_ID')
        
        if not monthly_price_id:
            return "Payment configuration error. Please contact support.", 500
        
        # Create checkout session - $29/month subscription
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': monthly_price_id, 
                    'quantity': 1,
                }
            ],
            mode='subscription',
            subscription_data={
                'description': 'Employee Suite - Shopify Inventory Automation'
            },
            allow_promotion_codes=True,
            success_url=url_for('billing.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('billing.subscribe', _external=True),
        )
        
        # Immediate redirect (don't wait for anything else)
        return redirect(checkout_session.url, code=303)
        
    except stripe.error.StripeError as e:
        # Stripe-specific errors
        return f"Payment error: {str(e)}. Please try again.", 500
    except Exception as e:
        # Other errors
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
            except Exception:
                pass
        except Exception:
            pass
    return render_template_string(SUCCESS_HTML)
