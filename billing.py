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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f6f6f7;
            color: #202223;
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
        .logo { font-size: 16px; font-weight: 600; color: #202223; text-decoration: none; letter-spacing: -0.2px; display: flex; align-items: center; gap: 10px; }
        .nav-btn { padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: 500; text-decoration: none; color: #6d7175; transition: background 0.15s; }
        .nav-btn:hover { background: #f6f6f7; color: #202223; }
        .container { max-width: 600px; margin: 0 auto; padding: 32px 24px; }
        .page-title { font-size: 28px; font-weight: 600; color: #202223; margin-bottom: 8px; letter-spacing: -0.3px; }
        .page-subtitle { font-size: 15px; color: #6d7175; margin-bottom: 32px; }
        .pricing-card { 
            background: #ffffff;
            border: 1px solid #e1e3e5;
            border-radius: 8px;
            padding: 32px;
        }
        .pricing-item {
            padding: 20px 0;
            border-bottom: 1px solid #e1e3e5;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .pricing-item:last-child { border-bottom: none; }
        .pricing-label { font-size: 15px; font-weight: 500; color: #202223; }
        .pricing-detail { font-size: 13px; color: #6d7175; margin-top: 4px; }
        .pricing-value { font-size: 24px; font-weight: 600; color: #202223; }
        .features-list { list-style: none; margin: 24px 0; padding: 24px 0; border-top: 1px solid #e1e3e5; }
        .features-list li {
            padding: 12px 0;
            font-size: 14px;
            color: #6d7175;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .features-list li:before { content: '✓'; color: #008060; font-weight: 600; font-size: 14px; }
        .btn {
            width: 100%;
            padding: 10px 16px;
            background: #008060;
            color: #fff;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.15s;
            margin-top: 8px;
        }
        .btn:hover { 
            background: #006e52;
        }
        
        /* Mobile */
        @media (max-width: 768px) {
            .container { padding: 24px 16px; }
            .page-title { font-size: 24px; }
            .pricing-card { padding: 24px; }
            .header-content { padding: 0 16px; height: 56px; }
        }
        @media (max-width: 480px) {
            .container { padding: 20px 12px; }
            .page-title { font-size: 20px; }
            .pricing-item { flex-direction: column; align-items: flex-start; gap: 8px; }
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
        <div style="text-align: center; margin-bottom: 40px;">
            <h1 class="page-title" style="margin-bottom: 12px;">{% if not has_access %}Restore Full Access{% else %}Unlock All Features{% endif %}</h1>
            <p class="page-subtitle" style="max-width: 600px; margin: 0 auto;">
                {% if not has_access %}
                Your trial has ended. Subscribe now to restore full access to all Employee Suite features.
                {% elif trial_active and not is_subscribed %}
                Your free trial is active ({{ days_left }} day{{ 's' if days_left != 1 else '' }} remaining). Subscribe now to ensure uninterrupted access when your trial ends.
                {% else %}
                Get unlimited access to all Employee Suite features for just $29/month.
                {% endif %}
            </p>
        </div>
        
        
        {% if not has_access %}
        <div style="padding: 16px; background: #f6f6f7; border-radius: 8px; border-left: 3px solid #c9cccf; color: #6d7175; font-size: 14px; line-height: 1.6; margin-bottom: 24px;">
            <div style="font-weight: 600; color: #202223; margin-bottom: 8px;">Your access has expired</div>
            <div>Subscribe to continue using Employee Suite and restore access to all features.</div>
        </div>
        {% elif trial_active and not is_subscribed %}
        <div style="padding: 16px; background: linear-gradient(135deg, #f0fdf4 0%, #e3fcef 100%); border-radius: 8px; border-left: 3px solid #008060; color: #006e52; font-size: 14px; line-height: 1.6; margin-bottom: 12px;">
            <div style="font-weight: 600; color: #008060; margin-bottom: 8px;">{{ days_left }} day{{ 's' if days_left != 1 else '' }} left in your trial</div>
            <div style="color: #006e52;">Subscribe now to avoid interruption and maintain access to all features.</div>
        </div>
        {% endif %}
        
        <div class="pricing-card">
            <div style="background: #ffffff; border: 1px solid #e1e3e5; border-radius: 8px; padding: 32px; margin-bottom: 24px; text-align: center;">
                <div style="font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #6d7175; margin-bottom: 12px;">Monthly Subscription</div>
                <div style="font-size: 48px; font-weight: 700; color: #202223; margin-bottom: 8px; line-height: 1;">$29<span style="font-size: 20px; font-weight: 500; color: #6d7175;">/month</span></div>
                <div style="font-size: 14px; color: #6d7175; margin-bottom: 24px;">7-day free trial • No setup fees • Cancel anytime</div>
            </div>
            
            <div style="background: #ffffff; border: 1px solid #e1e3e5; border-radius: 8px; padding: 24px; margin-bottom: 24px;">
                <div style="font-size: 16px; font-weight: 600; color: #202223; margin-bottom: 20px;">Everything you need to manage your store:</div>
                <div style="display: flex; flex-direction: column; gap: 16px;">
                    <div style="display: flex; align-items: start; gap: 12px;">
                        <span style="color: #008060; font-weight: 600; font-size: 16px; margin-top: 2px;">✓</span>
                        <div>
                            <div style="font-size: 15px; font-weight: 500; color: #202223; margin-bottom: 4px;">Order Monitoring & Tracking</div>
                            <div style="font-size: 13px; color: #6d7175;">Track pending orders, monitor fulfillment status, and never miss an order that needs attention.</div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: start; gap: 12px;">
                        <span style="color: #008060; font-weight: 600; font-size: 16px; margin-top: 2px;">✓</span>
                        <div>
                            <div style="font-size: 15px; font-weight: 500; color: #202223; margin-bottom: 4px;">Inventory Management with Alerts</div>
                            <div style="font-size: 13px; color: #6d7175;">Monitor stock levels across all products. Get instant alerts when inventory runs low.</div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: start; gap: 12px;">
                        <span style="color: #008060; font-weight: 600; font-size: 16px; margin-top: 2px;">✓</span>
                        <div>
                            <div style="font-size: 15px; font-weight: 500; color: #202223; margin-bottom: 4px;">Revenue Analytics & Reporting</div>
                            <div style="font-size: 13px; color: #6d7175;">Generate comprehensive revenue reports with product-level breakdown and performance insights.</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div style="background: linear-gradient(135deg, #e3fcef 0%, #d1fae5 100%); border: 1px solid #86efac; border-radius: 8px; padding: 24px; margin-bottom: 24px; text-align: center;">
                <div style="font-size: 16px; font-weight: 600; color: #008060; margin-bottom: 8px; letter-spacing: -0.2px;">7-Day Money-Back Guarantee</div>
                <div style="font-size: 14px; color: #006e52; line-height: 1.5;">Try it risk-free. If Employee Suite doesn't meet your needs, we'll refund your payment—no questions asked.</div>
            </div>
            
            <form method="POST" action="/create-checkout-session">
                <button type="submit" class="btn">
                    {% if not has_access %}
                    Restore Access Now
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
                'description': 'Employee Suite - Shopify Store Monitoring & Analytics'
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
