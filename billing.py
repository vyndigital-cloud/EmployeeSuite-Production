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
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 50%, #f0f4f8 100%);
            background-attachment: fixed;
            color: #171717;
            line-height: 1.6;
        }
        .header { 
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(0, 0, 0, 0.06);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 32px;
            height: 72px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo { font-size: 18px; font-weight: 600; color: #0a0a0a; text-decoration: none; letter-spacing: -0.4px; display: flex; align-items: center; gap: 10px; }
        .nav-btn { padding: 10px 18px; border-radius: 8px; font-size: 14px; font-weight: 500; text-decoration: none; color: #525252; transition: all 0.2s ease; }
        .nav-btn:hover { background: rgba(0, 0, 0, 0.04); color: #0a0a0a; }
        .container { max-width: 640px; margin: 0 auto; padding: 80px 32px; }
        .page-title { font-size: 48px; font-weight: 700; color: #0a0a0a; margin-bottom: 12px; letter-spacing: -1px; line-height: 1.1; }
        .page-subtitle { font-size: 18px; color: #64748b; margin-bottom: 64px; }
        .pricing-card { 
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 1) 100%);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-radius: 24px;
            padding: 48px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
        }
        .pricing-item {
            padding: 28px 0;
            border-bottom: 1px solid rgba(0, 0, 0, 0.06);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .pricing-item:last-child { border-bottom: none; }
        .pricing-label { font-size: 16px; font-weight: 600; color: #0a0a0a; }
        .pricing-detail { font-size: 14px; color: #64748b; margin-top: 6px; }
        .pricing-value { font-size: 32px; font-weight: 700; color: #0a0a0a; letter-spacing: -0.5px; }
        .features-list { list-style: none; margin: 40px 0; padding: 40px 0; border-top: 1px solid rgba(0, 0, 0, 0.06); }
        .features-list li {
            padding: 16px 0;
            font-size: 15px;
            color: #475569;
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .features-list li:before { content: '✓'; color: #10b981; font-weight: 700; font-size: 16px; }
        .btn {
            width: 100%;
            padding: 16px 24px;
            background: linear-gradient(135deg, #0a0a0a 0%, #262626 100%);
            color: #fff;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-top: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        .btn:hover { 
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        }
        
        /* Mobile */
        @media (max-width: 768px) {
            .container { padding: 48px 24px; }
            .page-title { font-size: 36px; }
            .pricing-card { padding: 40px 32px; }
            .header-content { padding: 0 24px; height: 64px; }
        }
        @media (max-width: 480px) {
            .container { padding: 40px 20px; }
            .page-title { font-size: 28px; }
            .pricing-item { flex-direction: column; align-items: flex-start; gap: 8px; }
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
        <div style="text-align: center; margin-bottom: 40px;">
            <h1 class="page-title" style="margin-bottom: 12px;">{% if not has_access %}Restore Access{% else %}Ready to Subscribe?{% endif %}</h1>
            <p class="page-subtitle" style="max-width: 600px; margin: 0 auto;">
                {% if not has_access %}
                Your trial has ended. Subscribe now to restore full access to Employee Suite.
                {% elif trial_active and not is_subscribed %}
                Your free trial is active ({{ days_left }} day{{ 's' if days_left != 1 else '' }} remaining). Subscribe now to ensure uninterrupted access when your trial ends.
                {% else %}
                Get unlimited access to all Employee Suite features.
                {% endif %}
            </p>
        </div>
        
        
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
            <div style="background: #fff; border: 1px solid #e5e5e5; border-radius: 16px; padding: 32px; margin-bottom: 24px; text-align: center;">
                <div style="font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #737373; margin-bottom: 12px;">Monthly Subscription</div>
                <div style="font-size: 48px; font-weight: 700; color: #0a0a0a; margin-bottom: 8px; line-height: 1;">$29<span style="font-size: 20px; font-weight: 500; color: #737373;">/month</span></div>
                <div style="font-size: 15px; color: #737373; margin-bottom: 24px;">7-day free trial • No setup fees • Cancel anytime</div>
            </div>
            
            <div style="background: #fff; border: 1px solid #e5e5e5; border-radius: 16px; padding: 24px; margin-bottom: 24px;">
                <div style="font-size: 16px; font-weight: 600; color: #0a0a0a; margin-bottom: 20px;">What's included:</div>
                <div style="display: flex; flex-direction: column; gap: 12px;">
                    <div style="display: flex; align-items: center; gap: 12px; font-size: 14px; color: #525252;">
                        <span style="color: #16a34a; font-weight: 700;">✓</span>
                        <span>Order monitoring and tracking</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px; font-size: 14px; color: #525252;">
                        <span style="color: #16a34a; font-weight: 700;">✓</span>
                        <span>Inventory management with low-stock alerts</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px; font-size: 14px; color: #525252;">
                        <span style="color: #16a34a; font-weight: 700;">✓</span>
                        <span>Revenue analytics and reporting</span>
                    </div>
                </div>
            </div>
            
            <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 12px; padding: 16px; margin-bottom: 24px; text-align: center;">
                <div style="font-size: 14px; font-weight: 600; color: #166534; margin-bottom: 4px;">✓ 7-Day Money-Back Guarantee</div>
                <div style="font-size: 13px; color: #15803d;">Try it risk-free. If it's not for you, we'll refund your payment.</div>
            </div>
            
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
