"""
Enhanced Billing System for Employee Suite
Two-tier pricing: Manual ($9.95) and Automated ($29)
"""
from flask import Blueprint, render_template_string, request, redirect, url_for, session, Response
from flask_login import login_required, current_user
from models import db, User, ShopifyStore
from enhanced_models import SubscriptionPlan, PLAN_MANUAL, PLAN_AUTOMATED
from datetime import datetime, timedelta
from logging_config import logger
import os

enhanced_billing_bp = Blueprint('enhanced_billing', __name__)

# Pricing
PREMIUM_PLAN_PRICE = 99.00  # USD/month
TRIAL_DAYS = 7  # 7-day free trial

def safe_redirect(url, shop=None, host=None):
    """Safe redirect for embedded/standalone contexts"""
    is_embedded = bool(host) or bool(shop) or request.args.get('embedded') == '1'
    
    if is_embedded:
        redirect_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Redirecting...</title>
    <script>
        if (window.top !== window.self) {{
            window.top.location.href = '{url}';
        }} else {{
            window.location.href = '{url}';
        }}
    </script>
</head>
<body>
    <p>Redirecting... <a href="{url}">Click here if not redirected</a></p>
</body>
</html>"""
        return Response(redirect_html, mimetype='text/html')
    else:
        from flask import redirect as flask_redirect
        return flask_redirect(url)

@enhanced_billing_bp.route('/pricing', methods=['GET'])
def pricing_page():
    """Pricing page with two-tier plans"""
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Pricing - Employee Suite</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f6f6f7;
                color: #202223;
                line-height: 1.5;
            }
            .header {
                background: #ffffff;
                border-bottom: 1px solid #e1e3e5;
                padding: 20px 0;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 20px;
            }
            .pricing-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 24px;
                margin-top: 40px;
            }
            .pricing-card {
                background: #ffffff;
                border: 2px solid #e1e3e5;
                border-radius: 8px;
                padding: 32px;
                position: relative;
            }
            .pricing-card.featured {
                border-color: #008060;
                box-shadow: 0 4px 12px rgba(0, 128, 96, 0.1);
            }
            .plan-name {
                font-size: 24px;
                font-weight: 600;
                color: #202223;
                margin-bottom: 8px;
            }
            .plan-price {
                font-size: 48px;
                font-weight: 700;
                color: #008060;
                margin: 16px 0;
            }
            .plan-price small {
                font-size: 18px;
                color: #6d7175;
                font-weight: 400;
            }
            .plan-features {
                list-style: none;
                margin: 24px 0;
            }
            .plan-features li {
                padding: 8px 0;
                color: #525252;
            }
            .plan-features li:before {
                content: "✓ ";
                color: #008060;
                font-weight: 600;
                margin-right: 8px;
            }
            .btn {
                display: inline-block;
                width: 100%;
                padding: 12px 24px;
                background: #008060;
                color: #ffffff;
                text-align: center;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 500;
                margin-top: 16px;
                transition: background 0.2s;
            }
            .btn:hover {
                background: #006e52;
            }
            .btn-secondary {
                background: #6d7175;
            }
            .btn-secondary:hover {
                background: #525252;
            }
            .trial-badge {
                background: #f0fdf4;
                color: #166534;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                margin-bottom: 16px;
                display: inline-block;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="container">
                <h1 style="font-size: 28px; font-weight: 600;">Employee Suite Pricing</h1>
                <p style="color: #6d7175; margin-top: 8px;">Choose the plan that works for you</p>
            </div>
        </div>
        
        <div class="container">
            <div class="trial-badge">🎉 7-Day Free Trial - No Credit Card Required</div>
            
            <div class="pricing-grid">
                <!-- Premium Plan -->
                <div class="pricing-card featured" style="max-width: 500px; margin: 0 auto;">
                    <div style="position: absolute; top: 16px; right: 16px; background: #008060; color: white; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600;">PREMIUM</div>
                    <div class="plan-name">Employee Suite Premium</div>
                    <div class="plan-price">$99<small>/month</small></div>
                    <ul class="plan-features">
                        <li>Order processing & automation</li>
                        <li>Inventory management & alerts</li>
                        <li>Revenue reports & analytics</li>
                        <li>CSV exports with date filtering</li>
                        <li>Auto-download reports</li>
                        <li>Scheduled reports (Email/SMS)</li>
                        <li>Multi-store connections</li>
                        <li>Staff connections</li>
                        <li>Priority support</li>
                        <li>Data encryption</li>
                    </ul>
                    <a href="/subscribe?plan=premium" class="btn">Start Free Trial</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

# NOTE: These routes are disabled to prevent conflicts with billing.py
# The app uses url_for('billing.subscribe') which requires the billing_bp routes
#
# @enhanced_billing_bp.route('/subscribe', methods=['GET'])
# @login_required
# def subscribe():
#     """Subscribe to premium plan - DISABLED, using billing.py version"""
#     pass
#
# @enhanced_billing_bp.route('/billing/confirm', methods=['GET'])
# @login_required
# def confirm_subscription():
#     """Confirm subscription - DISABLED, using billing.py version"""
#     pass

