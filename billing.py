from flask import Blueprint, render_template_string, request, redirect, url_for
from flask_login import login_required, current_user
import stripe
import os

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
        h1 { color: #667eea; margin-bottom: 20px; }
        .pricing { margin: 30px 0; }
        .price-item { padding: 15px; background: #f8f9fa; border-radius: 8px; margin: 10px 0; }
        .price-item .label { color: #666; font-size: 14px; }
        .price-item .amount { font-size: 2em; color: #667eea; font-weight: bold; }
        .total { font-size: 1.5em; color: #333; margin: 20px 0; padding: 20px; background: #fff3cd; border-radius: 8px; text-align: center; }
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
    return render_template_string(CHECKOUT_HTML)

@billing_bp.route('/create-checkout', methods=['POST'])
@login_required
def create_checkout():
    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': 'price_1SZ9FQ0VeS183a3ujDtFI9VF',
                    'quantity': 1,
                },
                {
                    'price': 'price_1SZ9FQ0VeS183a3uFSdAiXSQ',
                    'quantity': 1,
                }
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
            <p>Check your email for next steps and onboarding details.</p>
            <a href="{{ url_for('dashboard') }}" class="btn">Go to Dashboard →</a>
        </div>
    </body>
    </html>
    """)
