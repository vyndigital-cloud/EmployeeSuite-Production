"""
Enhanced Billing System for Employee Suite
Three-tier pricing: Free ($0), Pro ($29), Business ($99)
"""
from flask import Blueprint, render_template_string, request, redirect, url_for, session, Response
from flask_login import login_required, current_user
from models import db, User, ShopifyStore
from enhanced_models import (
    SubscriptionPlan, PLAN_FREE, PLAN_PRO, PLAN_BUSINESS,
    PLAN_PRICES, PLAN_FEATURES, PLAN_MANUAL, PLAN_AUTOMATED
)
from datetime import datetime, timedelta
from logging_config import logger
import os

enhanced_billing_bp = Blueprint('enhanced_billing', __name__)

# Pricing Constants
PRICE_FREE = 0.00
PRICE_PRO = 29.00
PRICE_BUSINESS = 99.00
TRIAL_DAYS = 7  # 7-day free trial for paid plans

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
    """Pricing page with three-tier plans: Free, Pro, Business"""
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
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #202223;
                line-height: 1.6;
            }
            .header {
                background: rgba(255,255,255,0.95);
                backdrop-filter: blur(10px);
                padding: 24px 0;
                box-shadow: 0 2px 20px rgba(0,0,0,0.1);
            }
            .header-content {
                max-width: 1200px;
                margin: 0 auto;
                padding: 0 24px;
                text-align: center;
            }
            .header h1 {
                font-size: 36px;
                font-weight: 700;
                color: #1a1a2e;
                margin-bottom: 8px;
            }
            .header p {
                color: #6b7280;
                font-size: 18px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 60px 24px;
            }
            .trial-badge {
                background: linear-gradient(135deg, #10b981, #059669);
                color: white;
                padding: 12px 24px;
                border-radius: 50px;
                font-size: 15px;
                font-weight: 600;
                display: inline-block;
                margin-bottom: 48px;
                box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
            }
            .pricing-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 24px;
                align-items: stretch;
            }
            @media (max-width: 900px) {
                .pricing-grid {
                    grid-template-columns: 1fr;
                    max-width: 400px;
                    margin: 0 auto;
                }
            }
            .pricing-card {
                background: #ffffff;
                border-radius: 20px;
                padding: 40px 32px;
                position: relative;
                transition: transform 0.3s, box-shadow 0.3s;
                display: flex;
                flex-direction: column;
            }
            .pricing-card:hover {
                transform: translateY(-8px);
                box-shadow: 0 20px 40px rgba(0,0,0,0.15);
            }
            .pricing-card.featured {
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: white;
                transform: scale(1.05);
                box-shadow: 0 25px 50px rgba(0,0,0,0.25);
            }
            .pricing-card.featured:hover {
                transform: scale(1.05) translateY(-8px);
            }
            .pricing-card.featured .plan-name,
            .pricing-card.featured .plan-desc,
            .pricing-card.featured .plan-features li {
                color: rgba(255,255,255,0.9);
            }
            .pricing-card.featured .plan-price {
                color: #10b981;
            }
            .badge {
                position: absolute;
                top: -12px;
                left: 50%;
                transform: translateX(-50%);
                background: linear-gradient(135deg, #f59e0b, #d97706);
                color: white;
                padding: 6px 20px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .plan-name {
                font-size: 28px;
                font-weight: 700;
                color: #1a1a2e;
                margin-bottom: 8px;
            }
            .plan-desc {
                font-size: 14px;
                color: #6b7280;
                margin-bottom: 24px;
            }
            .plan-price {
                font-size: 56px;
                font-weight: 800;
                color: #1a1a2e;
                margin-bottom: 8px;
                line-height: 1;
            }
            .plan-price span {
                font-size: 18px;
                font-weight: 500;
                color: #9ca3af;
            }
            .plan-features {
                list-style: none;
                margin: 32px 0;
                flex-grow: 1;
            }
            .plan-features li {
                padding: 12px 0;
                color: #374151;
                font-size: 15px;
                display: flex;
                align-items: center;
                border-bottom: 1px solid #f3f4f6;
            }
            .pricing-card.featured .plan-features li {
                border-bottom-color: rgba(255,255,255,0.1);
            }
            .plan-features li:last-child {
                border-bottom: none;
            }
            .plan-features li::before {
                content: "";
                width: 20px;
                height: 20px;
                background: linear-gradient(135deg, #10b981, #059669);
                border-radius: 50%;
                margin-right: 12px;
                flex-shrink: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='white'%3E%3Cpath fill-rule='evenodd' d='M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z' clip-rule='evenodd'/%3E%3C/svg%3E");
                background-size: 12px;
                background-position: center;
                background-repeat: no-repeat;
            }
            .plan-features li.disabled {
                color: #d1d5db;
                text-decoration: line-through;
            }
            .plan-features li.disabled::before {
                background: #e5e7eb;
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%239ca3af'%3E%3Cpath fill-rule='evenodd' d='M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z' clip-rule='evenodd'/%3E%3C/svg%3E");
            }
            .btn {
                display: block;
                width: 100%;
                padding: 16px 24px;
                text-align: center;
                text-decoration: none;
                border-radius: 12px;
                font-weight: 600;
                font-size: 16px;
                transition: all 0.3s;
                border: none;
                cursor: pointer;
            }
            .btn-primary {
                background: linear-gradient(135deg, #10b981, #059669);
                color: white;
                box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
            }
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(16, 185, 129, 0.5);
            }
            .btn-secondary {
                background: #f3f4f6;
                color: #374151;
            }
            .btn-secondary:hover {
                background: #e5e7eb;
            }
            .btn-featured {
                background: linear-gradient(135deg, #f59e0b, #d97706);
                color: white;
                box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
            }
            .btn-featured:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(245, 158, 11, 0.5);
            }
            .guarantee {
                text-align: center;
                margin-top: 48px;
                padding: 24px;
                background: rgba(255,255,255,0.1);
                border-radius: 12px;
                color: white;
            }
            .guarantee h3 {
                font-size: 18px;
                margin-bottom: 8px;
            }
            .guarantee p {
                font-size: 14px;
                opacity: 0.8;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <h1>Simple, Transparent Pricing</h1>
                <p>Choose the perfect plan for your Shopify store</p>
            </div>
        </div>

        <div class="container">
            <div style="text-align: center;">
                <div class="trial-badge">7-Day Free Trial on Paid Plans - No Credit Card Required</div>
            </div>

            <div class="pricing-grid">
                <!-- FREE Plan -->
                <div class="pricing-card">
                    <div class="plan-name">Free</div>
                    <div class="plan-desc">Perfect for getting started</div>
                    <div class="plan-price">$0<span>/month</span></div>
                    <ul class="plan-features">
                        <li>Dashboard with live data</li>
                        <li>Orders report (view only)</li>
                        <li>Inventory tracking</li>
                        <li>Revenue overview</li>
                        <li>1 store connection</li>
                        <li>7 days data history</li>
                        <li class="disabled">CSV exports</li>
                        <li class="disabled">Scheduled reports</li>
                        <li class="disabled">Priority support</li>
                    </ul>
                    <a href="/register" class="btn btn-secondary">Get Started Free</a>
                </div>

                <!-- PRO Plan -->
                <div class="pricing-card featured">
                    <div class="badge">Most Popular</div>
                    <div class="plan-name">Pro</div>
                    <div class="plan-desc">For growing businesses</div>
                    <div class="plan-price">$29<span>/month</span></div>
                    <ul class="plan-features">
                        <li>Everything in Free</li>
                        <li>CSV exports (all reports)</li>
                        <li>Date range filtering</li>
                        <li>Auto-download reports</li>
                        <li>Low-stock alerts</li>
                        <li>Up to 3 store connections</li>
                        <li>90 days data history</li>
                        <li class="disabled">Scheduled email reports</li>
                        <li class="disabled">Priority support</li>
                    </ul>
                    <a href="/subscribe?plan=pro" class="btn btn-featured">Start Free Trial</a>
                </div>

                <!-- BUSINESS Plan -->
                <div class="pricing-card">
                    <div class="plan-name">Business</div>
                    <div class="plan-desc">For power users & agencies</div>
                    <div class="plan-price">$99<span>/month</span></div>
                    <ul class="plan-features">
                        <li>Everything in Pro</li>
                        <li>Scheduled email reports</li>
                        <li>Daily/weekly/monthly delivery</li>
                        <li>SMS notifications</li>
                        <li>Unlimited stores</li>
                        <li>Unlimited data history</li>
                        <li>API access</li>
                        <li>Priority support</li>
                        <li>Custom report branding</li>
                    </ul>
                    <a href="/subscribe?plan=business" class="btn btn-primary">Start Free Trial</a>
                </div>
            </div>

            <div class="guarantee">
                <h3>30-Day Money-Back Guarantee</h3>
                <p>Try any paid plan risk-free. If you're not satisfied, get a full refund within 30 days.</p>
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

