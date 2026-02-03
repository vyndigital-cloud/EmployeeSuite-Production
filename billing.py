"""
Shopify Billing Integration
MANDATORY: All Shopify App Store apps MUST use Shopify Billing API
Stripe/external payment processors are NOT allowed for embedded apps
"""

import hashlib
import os
import secrets
from datetime import datetime

from flask import (
    Blueprint,
    Response,
    jsonify,
    redirect,
    render_template,  # Changed from render_template_string
    render_template_string,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

# Add error handling for imports
try:
    from enhanced_models import PLAN_PRICES, SubscriptionPlan
except ImportError as e:
    # Log the error so we know it's missing
    import logging
    logging.getLogger(__name__).warning(f"Could not import enhanced_models: {e}. Using fallback defaults.")
    
    PLAN_PRICES = {"pro": 39.00, "business": 99.00}

    class SubscriptionPlan:
        """Fallback class when enhanced_models is missing"""
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
        
        @staticmethod
        def query():
            class MockQuery:
                def filter_by(self, **kwargs):
                    return self
                def first(self):
                    return None
            return MockQuery()


from logging_config import logger
from models import ShopifyStore, User, db
from shopify_utils import normalize_shop_url

billing_bp = Blueprint("billing", __name__)

# Shopify Billing API configuration
from config import SHOPIFY_API_VERSION

APP_URL = os.getenv("SHOPIFY_APP_URL", "https://employeesuite-production.onrender.com")


def safe_redirect(url, shop=None, host=None):
    """Safe redirect for embedded/standalone contexts - App Bridge compliant"""
    is_embedded = bool(host) or bool(shop) or request.args.get("embedded") == "1"
    if is_embedded:
        redirect_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Redirecting...</title>
    <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
    <script>
        (function() {{
            var targetUrl = '{url}';
            if (targetUrl.includes('myshopify.com') || targetUrl.includes('shopify.com')) {{
                if (window.shopify && window.shopify.Redirect) {{
                    window.shopify.Redirect.dispatch(window.shopify.Redirect.Action.REMOTE, targetUrl);
                }} else {{
                    window.location.href = targetUrl;
                }}
            }} else {{
                window.location.href = targetUrl;
            }}
        }})();
    </script>
</head>
<body>
    <p>Redirecting... <a href="{url}">Click here if not redirected</a></p>
</body>
</html>"""
        return Response(redirect_html, mimetype="text/html")
    else:
        return redirect(url)


# Plan configuration (Production Price: $39/month - competitive pricing)
PLANS = {
    "pro": {
        "name": "Employee Suite Pro",
        "price": 39.00,
        "features": [
            "🤖 AI-Powered Stockout Predictions",
            "📊 Real-Time Inventory Dashboard", 
            "📦 Smart Order Management",
            "💰 Revenue Analytics & Forecasting",
            "📥 Unlimited CSV Exports",
            "🔄 Automated Reorder Alerts",
            "📱 Mobile-Responsive Interface",
            "⚡ Real-Time Sync with Shopify",
            "🎯 Low Stock Notifications",
            "📈 Sales Velocity Analysis",
            "🛡️ Enterprise Security",
            "💬 Priority Email Support",
        ],
    },
}

SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Welcome to Employee Suite Pro!</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #202223;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 24px;
        }
        .success-container { 
            text-align: center; 
            max-width: 500px; 
            background: white;
            padding: 48px 32px;
            border-radius: 16px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        .success-icon {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, #e3fcef 0%, #d1fae5 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            margin: 0 auto 24px;
            animation: bounce 1s ease-in-out;
        }
        @keyframes bounce {
            0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
            40% { transform: translateY(-10px); }
            60% { transform: translateY(-5px); }
        }
        .success-title { 
            font-size: 32px; 
            font-weight: 700; 
            color: #202223; 
            margin-bottom: 16px; 
        }
        .success-text { 
            font-size: 18px; 
            color: #6d7175; 
            line-height: 1.6; 
            margin-bottom: 32px; 
        }
        .btn {
            padding: 16px 32px;
            background: linear-gradient(135deg, #008060 0%, #00a86b 100%);
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            text-decoration: none;
            display: inline-block;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .trial-info {
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 24px;
            font-size: 14px;
            color: #0369a1;
        }
    </style>
</head>
<body>
    <div class="success-container">
        <div class="success-icon">🎉</div>
        <h1 class="success-title">Welcome to Employee Suite Pro!</h1>
        <div class="trial-info">
            <strong>Your 7-day free trial has started!</strong><br>
            Full access to all features until {{ trial_end_date }}
        </div>
        <p class="success-text">
            Your subscription is now active and you have full access to all Employee Suite features. 
            Start exploring your dashboard to see how we can transform your store operations.
        </p>
        <a href="{{ dashboard_url }}" class="btn">🚀 Go to Dashboard</a>
    </div>
    
    <script>
        // Auto-redirect after 5 seconds
        setTimeout(function() {
            window.location.href = "{{ dashboard_url }}";
        }, 5000);
    </script>
</body>
</html>
"""

# Enhanced subscribe page template
SUBSCRIBE_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Subscribe to Employee Suite Pro</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #202223;
            -webkit-font-smoothing: antialiased;
            line-height: 1.6;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .subscribe-card {
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            width: 100%;
            max-width: 800px;
        }
        
        .header {
            background: linear-gradient(135deg, #008060 0%, #00a86b 100%);
            color: white;
            padding: 40px;
            text-align: center;
            position: relative;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="white" opacity="0.1"/><circle cx="75" cy="75" r="1" fill="white" opacity="0.1"/><circle cx="50" cy="10" r="0.5" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
            opacity: 0.3;
        }
        
        .header-content {
            position: relative;
            z-index: 1;
        }
        
        .logo {
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }
        
        .tagline {
            font-size: 18px;
            opacity: 0.9;
            font-weight: 400;
        }
        
        .content {
            padding: 50px 40px;
        }
        
        .urgency-banner {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
            color: white;
            padding: 16px;
            text-align: center;
            margin-bottom: 32px;
            border-radius: 8px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.02); }
            100% { transform: scale(1); }
        }
        
        .urgency-text {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 4px;
        }
        
        .urgency-subtext {
            font-size: 14px;
            opacity: 0.9;
        }
        
        .plan-header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .trial-badge {
            display: inline-block;
            background: #e3fcef;
            color: #008060;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 16px;
        }
        
        .plan-name {
            font-size: 32px;
            font-weight: 700;
            color: #202223;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }
        
        .plan-price {
            font-size: 48px;
            font-weight: 800;
            color: #008060;
            margin-bottom: 8px;
            letter-spacing: -1px;
        }
        
        .plan-price .currency {
            font-size: 32px;
            vertical-align: top;
        }
        
        .plan-price .period {
            font-size: 18px;
            font-weight: 500;
            color: #6d7175;
            vertical-align: bottom;
        }
        
        .social-proof {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 32px;
            text-align: center;
        }
        
        .social-proof-title {
            font-size: 18px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 16px;
        }
        
        .testimonial {
            font-style: italic;
            color: #6d7175;
            margin-bottom: 12px;
            font-size: 16px;
        }
        
        .testimonial-author {
            font-size: 14px;
            font-weight: 600;
            color: #008060;
        }
        
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }
        
        .feature-item {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 16px;
            background: #f9fafb;
            border-radius: 8px;
            transition: transform 0.2s ease;
        }
        
        .feature-item:hover {
            transform: translateY(-2px);
        }
        
        .feature-icon {
            width: 24px;
            height: 24px;
            background: #e3fcef;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            margin-top: 2px;
        }
        
        .feature-icon::before {
            content: '✓';
            color: #008060;
            font-weight: 700;
            font-size: 14px;
        }
        
        .feature-text {
            flex: 1;
        }
        
        .feature-title {
            font-size: 16px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 4px;
        }
        
        .feature-description {
            font-size: 14px;
            color: #6d7175;
            line-height: 1.5;
        }
        
        .cta-section {
            background: linear-gradient(135deg, #f6f6f7 0%, #e8f4f8 100%);
            border-radius: 16px;
            padding: 40px;
            text-align: center;
            margin-bottom: 32px;
            border: 2px solid #e3fcef;
        }
        
        .cta-title {
            font-size: 28px;
            font-weight: 700;
            color: #202223;
            margin-bottom: 12px;
        }
        
        .cta-subtitle {
            font-size: 18px;
            color: #6d7175;
            margin-bottom: 32px;
        }
        
        .subscribe-btn {
            background: linear-gradient(135deg, #008060 0%, #00a86b 100%);
            color: white;
            border: none;
            padding: 20px 40px;
            border-radius: 12px;
            font-size: 20px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            box-shadow: 0 8px 20px rgba(0, 128, 96, 0.3);
            position: relative;
            overflow: hidden;
            min-width: 280px;
        }
        
        .subscribe-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 30px rgba(0, 128, 96, 0.4);
        }
        
        .subscribe-btn:active {
            transform: translateY(-1px);
        }
        
        .subscribe-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }
        
        .subscribe-btn:hover::before {
            left: 100%;
        }
        
        .guarantee {
            margin-top: 24px;
        }
        
        .guarantee-text {
            font-size: 14px;
            color: #6d7175;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .guarantee-icon {
            width: 20px;
            height: 20px;
            background: #e3fcef;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .guarantee-icon::before {
            content: '🛡️';
            font-size: 12px;
        }
        
        .value-props {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin: 32px 0;
        }
        
        .value-prop {
            text-align: center;
            padding: 16px;
        }
        
        .value-prop-icon {
            font-size: 32px;
            margin-bottom: 8px;
        }
        
        .value-prop-text {
            font-size: 14px;
            font-weight: 600;
            color: #202223;
        }
        
        .back-link {
            text-align: center;
            margin-top: 32px;
        }
        
        .back-link a {
            color: #6d7175;
            text-decoration: none;
            font-size: 14px;
            transition: color 0.2s;
        }
        
        .back-link a:hover {
            color: #008060;
        }
        
        .error-banner {
            background: #fff4f4;
            border: 1px solid #fecaca;
            color: #dc2626;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 24px;
            text-align: center;
        }
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
            .container { padding: 20px 16px; }
            .content { padding: 32px 24px; }
            .header { padding: 32px 24px; }
            .plan-price { font-size: 40px; }
            .plan-name { font-size: 28px; }
            .features-grid { grid-template-columns: 1fr; gap: 16px; }
            .cta-section { padding: 32px 24px; }
            .subscribe-btn { width: 100%; padding: 18px; min-width: auto; }
            .cta-title { font-size: 24px; }
            .cta-subtitle { font-size: 16px; }
        }
        
        @media (max-width: 480px) {
            .logo { font-size: 24px; }
            .tagline { font-size: 16px; }
            .plan-price { font-size: 36px; }
            .plan-name { font-size: 24px; }
            .urgency-text { font-size: 16px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="subscribe-card">
            <div class="header">
                <div class="header-content">
                    <div class="logo">Employee Suite</div>
                    <div class="tagline">Streamline Your Shopify Operations</div>
                </div>
            </div>
            
            <div class="content">
                <!-- Error Banner -->
                {% if error %}
                <div class="error-banner">
                    <strong>⚠️ {{ error }}</strong>
                </div>
                {% endif %}
                
                <!-- Urgency Banner -->
                <div class="urgency-banner">
                    <div class="urgency-text">🔥 Limited Time: 7-Day Free Trial</div>
                    <div class="urgency-subtext">Join 500+ store owners who transformed their operations</div>
                </div>
                
                <div class="plan-header">
                    <div class="trial-badge">✨ 7-Day Free Trial Included</div>
                    <div class="plan-name">{{ plan_name }}</div>
                    <div class="plan-price">
                        <span class="currency">$</span>{{ price }}<span class="period">/month</span>
                    </div>
                </div>
                
                <!-- Social Proof -->
                <div class="social-proof">
                    <div class="social-proof-title">🌟 Join 500+ Successful Shopify Store Owners</div>
                    <div class="testimonial">"Employee Suite transformed how we manage inventory. The automated reports save us 10+ hours every week!"</div>
                    <div class="testimonial-author">— Sarah M., Fashion Store Owner ($50K/month)</div>
                </div>
                
                <!-- Value Props -->
                <div class="value-props">
                    <div class="value-prop">
                        <div class="value-prop-icon">⚡</div>
                        <div class="value-prop-text">Setup in 2 minutes</div>
                    </div>
                    <div class="value-prop">
                        <div class="value-prop-icon">💰</div>
                        <div class="value-prop-text">Save 10+ hours/week</div>
                    </div>
                    <div class="value-prop">
                        <div class="value-prop-icon">📈</div>
                        <div class="value-prop-text">Increase revenue 15%</div>
                    </div>
                    <div class="value-prop">
                        <div class="value-prop-icon">🛡️</div>
                        <div class="value-prop-text">Enterprise security</div>
                    </div>
                </div>
                
                <div class="features-grid">
                    {% for feature in features %}
                    <div class="feature-item">
                        <div class="feature-icon"></div>
                        <div class="feature-text">
                            <div class="feature-title">{{ feature.split(' ', 1)[1] if ' ' in feature else feature }}</div>
                            <div class="feature-description">
                                {% if 'AI-Powered' in feature %}
                                Predict stockouts before they happen with machine learning
                                {% elif 'Real-Time' in feature %}
                                Live inventory tracking with instant low-stock alerts
                                {% elif 'Smart Order' in feature %}
                                Automated order processing and fulfillment workflows
                                {% elif 'Revenue' in feature %}
                                Comprehensive analytics with profit margin insights
                                {% elif 'CSV' in feature %}
                                Export any data with custom date ranges and filters
                                {% elif 'Automated' in feature %}
                                Schedule daily, weekly, or monthly report delivery
                                {% elif 'Mobile' in feature %}
                                Full-featured mobile interface for on-the-go management
                                {% elif 'Real-Time Sync' in feature %}
                                Instant synchronization with your Shopify store data
                                {% elif 'Low Stock' in feature %}
                                Smart notifications before you run out of inventory
                                {% elif 'Sales Velocity' in feature %}
                                Track product performance and sales trends
                                {% elif 'Enterprise' in feature %}
                                Bank-level encryption and data protection
                                {% elif 'Priority' in feature %}
                                Direct access to our support team via email
                                {% else %}
                                Professional tools to streamline your operations
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                
                <!-- Strong CTA Section -->
                <div class="cta-section">
                    <div class="cta-title">🚀 Ready to Transform Your Store?</div>
                    <div class="cta-subtitle">Start your free trial now and see results in 24 hours</div>
                    
                    {% if has_store and not error %}
                    <form method="POST" action="{{ url_for('billing.create_charge') }}">
                        {% if shop %}<input type="hidden" name="shop" value="{{ shop }}">{% endif %}
                        {% if host %}<input type="hidden" name="host" value="{{ host }}">{% endif %}
                        <input type="hidden" name="plan" value="{{ plan }}">
                        <button type="submit" class="subscribe-btn" id="subscribeBtn">
                            🎯 Start Free Trial & Subscribe Now
                        </button>
                    </form>
                    {% else %}
                    <a href="{{ url_for('shopify.shopify_settings', shop=shop, host=host) }}" class="subscribe-btn">
                        🔗 Connect Store First
                    </a>
                    {% endif %}
                    
                    <div class="guarantee">
                        <div class="guarantee-text">
                            <div class="guarantee-icon"></div>
                            <span>Cancel anytime • No setup fees • 24/7 support • 30-day money-back guarantee</span>
                        </div>
                    </div>
                </div>
                
                <div class="back-link">
                    <a href="{{ url_for('core.dashboard', shop=shop, host=host) }}">← Back to Dashboard</a>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const subscribeBtn = document.getElementById('subscribeBtn');
            
            if (subscribeBtn) {
                subscribeBtn.addEventListener('click', function(e) {
                    // Add loading state
                    this.innerHTML = '⏳ Creating your subscription...';
                    this.disabled = true;
                    
                    // Re-enable after timeout (in case of errors)
                    setTimeout(() => {
                        if (this.disabled) {
                            this.innerHTML = '🎯 Start Free Trial & Subscribe Now';
                            this.disabled = false;
                        }
                    }, 10000);
                });
            }
            
            // Add scroll animations
            const observerOptions = {
                threshold: 0.1,
                rootMargin: '0px 0px -50px 0px'
            };
            
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }
                });
            }, observerOptions);
            
            // Animate feature items
            document.querySelectorAll('.feature-item').forEach((item, index) => {
                item.style.opacity = '0';
                item.style.transform = 'translateY(20px)';
                item.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
                observer.observe(item);
            });
            
            // Add urgency timer (optional)
            const urgencyBanner = document.querySelector('.urgency-banner');
            if (urgencyBanner) {
                setInterval(() => {
                    urgencyBanner.style.transform = 'scale(1.02)';
                    setTimeout(() => {
                        urgencyBanner.style.transform = 'scale(1)';
                    }, 200);
                }, 3000);
            }
        });
    </script>
</body>
</html>
"""


def get_shop_and_token_for_user(user):
    """Get shop URL and access token for a user"""
    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    if store and store.is_connected():
        return store.shop_url, store.get_access_token()
    return None, None


def format_billing_error(error_msg):
    """Format billing error messages to be more user-friendly"""
    error_lower = error_msg.lower()

    if "422" in error_msg or "unprocessable" in error_lower:
        if "owned by a shop" in error_lower or "must be migrated" in error_lower:
            return """App Migration Required

Your app needs to be migrated to the Shopify Partners area before billing can work.

To fix this:
1. Go to https://partners.shopify.com
2. Navigate to your app → Settings
3. Look for "App ownership" section
4. Migrate the app from Shop ownership to Partners ownership
5. Once migrated, try subscribing again"""
        elif "managed pricing" in error_lower or "pricing" in error_lower:
            return "Billing setup issue: Please check your app's pricing settings in the Shopify Partners dashboard."
        else:
            return f"Unable to create subscription. Error: {error_msg[:100]}"
    elif "403" in error_msg or "forbidden" in error_lower:
        return "Permission denied: Your app may not have billing permissions."
    elif "401" in error_msg or "unauthorized" in error_lower:
        return "Authentication error: Please try reconnecting your Shopify store."
    else:
        return f"Subscription error: {error_msg[:150]}"


def create_recurring_charge(shop_url, access_token, return_url, plan_type="pro"):
    """Create a recurring application charge using Shopify GraphQL Admin API"""
    try:
        from shopify_graphql import ShopifyGraphQLClient

        plan = PLANS.get(plan_type, PLANS["pro"])
        client = ShopifyGraphQLClient(shop_url, access_token)

        is_dev_store = "-dev" in shop_url.lower() or "dev" in shop_url.lower()
        test_mode = (
            os.getenv("SHOPIFY_BILLING_TEST", "false").lower() == "true" or is_dev_store
        )

        mutation = """
        mutation AppSubscriptionCreate($name: String!, $lineItems: [AppSubscriptionLineItemInput!]!, $returnUrl: URL!, $test: Boolean, $trialDays: Int) {
            appSubscriptionCreate(name: $name, returnUrl: $returnUrl, lineItems: $lineItems, test: $test, trialDays: $trialDays) {
                appSubscription {
                    id
                    status
                }
                confirmationUrl
                userErrors {
                    field
                    message
                }
            }
        }
        """

        # Check if trial should be skipped
        skip_trial = request.form.get("skip_trial") == "true"
        trial_days = 0 if skip_trial else 7

        variables = {
            "name": f"Employee Suite {plan['name']}",
            "returnUrl": return_url,
            "test": test_mode,
            "trialDays": trial_days,
            "lineItems": [
                {
                    "plan": {
                        "appRecurringPricingDetails": {
                            "price": {"amount": plan["price"], "currencyCode": "USD"},
                            "interval": "EVERY_30_DAYS",
                        }
                    }
                }
            ],
        }

        logger.info(f"Creating {plan_type} plan charge (GraphQL) for {shop_url}")

        result = client.execute_query(mutation, variables)

        if "error" in result:
            return {"success": False, "error": result["error"]}

        data = result.get("appSubscriptionCreate", {})
        user_errors = data.get("userErrors", [])

        if user_errors:
            error_msg = "; ".join([e["message"] for e in user_errors])
            logger.error(f"GraphQL Billing error: {error_msg}")
            return {"success": False, "error": error_msg}

        subscription = data.get("appSubscription", {})
        # Extract numeric ID from GID if possible for backward compatibility,
        # but technically should store GID. The DB probably handles string.
        # GID format: gid://shopify/AppSubscription/123456
        
        from shopify_utils import parse_gid

        gid = subscription.get("id")
        # Ensure we return a clean ID for the database
        charge_id = parse_gid(gid)
        
        # Log if we got a GID but couldn't parse it (just for debugging)
        if gid and not charge_id:
            logger.warning(f"Could not parse numeric ID from subscription GID: {gid} for shop {shop_url}")
            # Fallback: store the full GID (safer than None)
            charge_id = gid
        
        # Ensure we have some form of ID
        if not charge_id:
            logger.error(f"No charge ID available from Shopify response for {shop_url}")
            return {"success": False, "error": "No subscription ID returned from Shopify"}

        return {
            "success": True,
            "charge_id": charge_id,
            "confirmation_url": data.get("confirmationUrl"),
            "status": subscription.get("status"),
        }

    except Exception as e:
        logger.error(f"Failed to create Shopify charge (GraphQL): {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def activate_recurring_charge(shop_url, access_token, charge_id):
    """
    Check if a charge is active (GraphQL).
    With appSubscriptionCreate, we don't need to manually 'activate' like in REST.
    We just verify the status is ACTIVE.
    """
    return get_charge_status(shop_url, access_token, charge_id)


def get_charge_status(shop_url, access_token, charge_id):
    """Get the status of a recurring charge using GraphQL"""
    try:
        from shopify_graphql import ShopifyGraphQLClient

        client = ShopifyGraphQLClient(shop_url, access_token)

        # Format ID as GID
        from shopify_utils import format_gid, parse_gid

        # Ensure we have a clean numeric ID first, then format as GID
        numeric_id = parse_gid(charge_id)
        if numeric_id:
            gid = format_gid(numeric_id, "AppSubscription")
        else:
            # Fallback to original if parsing failed (maybe it's a malformed string but we want to try)
            gid = charge_id

        query = """
        query GetSubscription($id: ID!) {
            node(id: $id) {
                ... on AppSubscription {
                    id
                    status
                }
            }
        }
        """

        variables = {"id": gid}
        result = client.execute_query(query, variables)

        if "error" in result:
            return {"success": False, "error": result["error"]}

        node = result.get("node", {})
        if not node:
            return {"success": False, "error": "Subscription not found"}

        return {
            "success": True,
            "status": node.get(
                "status", "UNKNOWN"
            ).lower(),  # REST used lowercase, GraphQL uses UPPERCASE usually
            "charge_id": charge_id,
        }
    except Exception as e:
        logger.error(f"Failed to get Shopify charge status (GraphQL): {e}")
        return {"success": False, "error": str(e)}


def cancel_app_subscription(shop_url, access_token, charge_id):
    """Cancel a recurring application charge using GraphQL"""
    try:
        from shopify_graphql import ShopifyGraphQLClient

        client = ShopifyGraphQLClient(shop_url, access_token)
        
        from shopify_utils import format_gid, parse_gid

        numeric_id = parse_gid(charge_id)
        if not numeric_id:
            return {"success": False, "error": "Invalid charge ID"}
            
        gid = format_gid(numeric_id, "AppSubscription")

        mutation = """
        mutation appSubscriptionCancel($id: ID!) {
          appSubscriptionCancel(id: $id) {
            appSubscription {
              id
              status
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        variables = {"id": gid}
        logger.info(f"Cancelling subscription {gid} for {shop_url}")

        result = client.execute_query(mutation, variables)

        if "error" in result:
            return {"success": False, "error": result["error"]}

        data = result.get("appSubscriptionCancel", {})
        user_errors = data.get("userErrors", [])

        if user_errors:
            error_msg = "; ".join([e["message"] for e in user_errors])
            logger.error(f"GraphQL Cancel error: {error_msg}")
            return {"success": False, "error": error_msg}

        return {"success": True}

    except Exception as e:
        logger.error(f"Failed to cancel Shopify subscription (GraphQL): {e}")
        return {"success": False, "error": str(e)}


@billing_bp.route("/billing/subscribe")
def subscribe():
    """Enhanced subscribe page with strong CTAs"""
    from shopify_utils import normalize_shop_url
    
    try:
        # Normalize shop URL first thing
        shop = request.args.get("shop", "").strip()
        if shop:
            shop = normalize_shop_url(shop)

        host = request.args.get("host", "").strip()
        plan_type = request.args.get("plan", "pro")
        
        # Validate plan type
        if plan_type not in PLANS:
            plan_type = "pro"
        
        plan = PLANS[plan_type]

        # Enhanced user detection
        user = None
        store = None
        try:
            if current_user.is_authenticated:
                user_id = current_user.get_id()
                if user_id:
                    user = User.query.get(int(user_id))
            
            # Try shop lookup for embedded apps
            if not user and shop:
                store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
                if store and store.user:
                    user = store.user
        except Exception as e:
            logger.error(f"Error finding user in subscribe: {e}")
            user = None

        # Get store if we have a user but no store yet
        if user and not store:
            store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()

        # Validate store connection
        has_store = False
        if store:
            access_token = store.get_access_token()
            if access_token:
                try:
                    from shopify_graphql import ShopifyGraphQLClient
                    client = ShopifyGraphQLClient(store.shop_url, access_token)
                    query = "query { shop { name } }"
                    result = client.execute_query(query)
                    if "error" not in result and "errors" not in result:
                        has_store = True
                    else:
                        logger.warning(f"Store connection validation failed for {store.shop_url}")
                        has_store = False
                except Exception as e:
                    logger.warning(f"Store connection check failed: {e}")
                    has_store = False

        # Set shop from store if not provided
        if not shop and store:
            shop = store.shop_url

        # Calculate user status
        trial_active = user.is_trial_active() if user else False
        has_access = user.has_access() if user else False
        days_left = 0
        if user and trial_active:
            try:
                days_left = (user.trial_ends_at - datetime.utcnow()).days
                days_left = max(0, days_left)
            except:
                days_left = 0
        
        # Determine error message
        error = request.args.get("error")
        if not has_store and not error:
            if store is None:
                error = "Please connect your Shopify store first to subscribe"
            else:
                error = "Store connection issue - please reconnect in Settings"

        # Template variables
        template_vars = {
            "trial_active": trial_active,
            "has_access": has_access,
            "days_left": days_left,
            "is_subscribed": user.is_subscribed if user else False,
            "shop": shop or "",
            "host": host or "",
            "has_store": has_store,
            "plan": plan_type,
            "plan_name": plan["name"],
            "price": int(plan["price"]),
            "features": plan["features"],
            "error": error,
            "config_api_key": os.getenv("SHOPIFY_API_KEY", ""),
        }

        return render_template_string(SUBSCRIBE_PAGE_HTML, **template_vars)
            
    except Exception as e:
        logger.error(f"Critical error in subscribe route: {e}", exc_info=True)
        return jsonify({
            "error": "Subscribe page temporarily unavailable",
            "message": "Please try again in a moment",
            "error_id": datetime.now().strftime('%Y%m%d_%H%M%S')
        }), 500


def validate_csrf_token():
    """Simple CSRF validation using centralized logic"""
    from shopify_utils import validate_csrf_token as validate_csrf
    return validate_csrf(request, session)


@billing_bp.route("/subscribe")
def subscribe_shortcut():
    """Subscribe page - uses Shopify Billing API"""
    from shopify_utils import normalize_shop_url
    
    shop = request.args.get("shop", "")
    if shop:
        shop = normalize_shop_url(shop)

    host = request.args.get("host", "")
    plan_type = request.args.get("plan", "pro")
    
    # Validate plan type
    if plan_type not in PLANS:
        plan_type = "pro"
    
    plan = PLANS[plan_type]

    return render_template(
        "subscribe.html",
        shop=shop,
        host=host,
        plan=plan_type,
        plan_name=plan["name"],
        price=int(plan["price"]),
        features=plan["features"],
        config_api_key=os.getenv("SHOPIFY_API_KEY"),
    )


@billing_bp.route("/create-charge", methods=["GET", "POST"])
@billing_bp.route("/billing/create-charge", methods=["GET", "POST"])
def create_charge():
    """Create a Shopify recurring charge"""
    from shopify_utils import normalize_shop_url
    
    # Normalize shop URL first thing
    shop = request.form.get("shop") or request.args.get("shop", "")
    if shop:
        shop = normalize_shop_url(shop)
    
    # Simple CSRF protection
    if not validate_csrf_token():
        logger.warning(f"CSRF validation failed for billing request from shop: {shop}")
        return redirect("/billing?error=invalid_request")

    host = request.form.get("host") or request.args.get("host", "")

    plan_type = request.form.get("plan") or request.args.get("plan", "pro")

    # Find user - improved logic for embedded apps
    user = None
    try:
        # First try current_user (for standalone mode)
        if current_user.is_authenticated:
            user_id = current_user.get_id()
            if user_id:
                user = User.query.get(int(user_id))
        
        # For embedded apps, also try finding by shop URL
        if not user and shop:
            store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
            if store and store.user:
                user = store.user
                logger.info(f"Found user {user.id} via shop lookup for {shop}")
        
        # Additional fallback: try to find any active store for the shop
        if not user and shop:
            all_stores = ShopifyStore.query.filter_by(shop_url=shop).all()
            for store in all_stores:
                if store.user and store.is_connected():
                    user = store.user
                    logger.info(f"Found user {user.id} via connected store fallback for {shop}")
                    break
                    
    except Exception as e:
        logger.error(f"Error finding user in create_charge: {e}")
        pass

    if not user:
        subscribe_url = url_for(
            "billing.subscribe",
            error="Please connect your Shopify store first.",
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)

    # Try to find the specific store for this shop first
    store = ShopifyStore.query.filter_by(user_id=user.id, shop_url=shop, is_active=True).first()

    # Fallback to any active store for the user
    if not store:
        store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
        logger.info(f"Using fallback store {store.shop_url if store else 'None'} for user {user.id}")
    
    if not store:
        logger.error(f"No active store found for user {user.id}")
        # Try to find ANY store for this user to get better error info
        any_store = ShopifyStore.query.filter_by(user_id=user.id).first()
        if any_store:
            error_msg = f"Store {any_store.shop_url} is not active. Please reconnect in Settings."
        else:
            error_msg = "No Shopify store connected. Please connect your store first."
        
        subscribe_url = url_for(
            "billing.subscribe",
            error=error_msg,
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)

    shop_url = store.shop_url

    access_token = store.get_access_token()
    
    if not access_token:
        logger.error(f"Store {shop_url} has no valid access token")
        settings_url = url_for(
            "shopify.shopify_settings",
            error="Store not connected. Please reconnect.",
            shop=shop_url,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop_url, host=host)

    # Optional: Test the connection with a simple API call
    try:
        from shopify_graphql import ShopifyGraphQLClient
        client = ShopifyGraphQLClient(shop_url, access_token)
        test_result = client.execute_query("query { shop { name } }")
        if "error" in test_result:
            logger.error(f"Store {shop_url} connection test failed: {test_result['error']}")
            settings_url = url_for(
                "shopify.shopify_settings",
                error="Store connection issue. Please reconnect.",
                shop=shop_url,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop_url, host=host)
    except Exception as e:
        logger.warning(f"Store connection test failed for {shop_url}: {e}")
        # Continue anyway - don't block on connection test failures

    if user.is_subscribed:
        dashboard_url = f"/dashboard?shop={shop_url}&host={host}"
        return safe_redirect(dashboard_url, shop=shop_url, host=host)

    return_url = (
        f"{APP_URL}/billing/confirm?shop={shop_url}&host={host}&plan={plan_type}"
    )

    result = create_recurring_charge(shop_url, access_token, return_url, plan_type)

    if not result.get("success"):
        error_msg = result.get("error", "Failed to create subscription")
        logger.error(f"Billing error for {shop_url}, user {user.id}, plan {plan_type}: {error_msg}")

        if (
            "owned by a shop" in error_msg.lower()
            or "must be migrated" in error_msg.lower()
        ):
            store.disconnect()
            db.session.commit()
            install_url = url_for("oauth.install", shop=shop_url, host=host)
            return render_template_string(f"""
            <!DOCTYPE html>
            <html><head><meta charset="utf-8"><title>Redirecting...</title>
            <script>window.location.href = '{install_url}';</script>
            </head><body><p>Redirecting...</p></body></html>
            """)

        formatted_error = format_billing_error(error_msg)
        return redirect(
            url_for(
                "billing.subscribe",
                error=formatted_error,
                shop=shop_url,
                host=host,
                plan=plan_type,
            )
        )

    store.charge_id = str(result["charge_id"])
    db.session.commit()

    logger.info(f"Created Shopify charge {result['charge_id']} for {shop_url}")

    confirmation_url = result["confirmation_url"]
    if host:
        return safe_redirect(confirmation_url, shop=shop_url, host=host)
    else:
        return redirect(confirmation_url)


@billing_bp.route("/billing/confirm")
def confirm_charge():
    """Handle return from Shopify after merchant approves/declines charge"""
    from shopify_utils import normalize_shop_url
    
    shop = request.args.get("shop", "")
    if shop:
        shop = normalize_shop_url(shop)

    host = request.args.get("host", "")

    charge_id = request.args.get("charge_id")
    plan_type = request.args.get("plan", "pro")

    if not charge_id:
        logger.warning("No charge_id in billing confirm callback")
        subscribe_url = url_for(
            "billing.subscribe",
            error="Missing charge information",
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)

    # Find user
    user = None
    try:
        if current_user.is_authenticated:
            user_id = current_user.get_id()
            if user_id:
                user = User.query.get(int(user_id))
        if not user and shop:
            store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
            if store and store.user:
                user = store.user
    except Exception:
        pass

    if not user:
        subscribe_url = url_for(
            "billing.subscribe",
            error="Please connect your Shopify store first.",
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)

    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    if not store:
        subscribe_url = url_for(
            "billing.subscribe",
            error="Store not found",
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)

    shop_url = store.shop_url
    access_token = store.get_access_token()
    if not access_token:
        subscribe_url = url_for(
            "billing.subscribe",
            error="Store not properly connected.",
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)

    status_result = get_charge_status(shop_url, access_token, charge_id)

    if not status_result.get("success"):
        store.charge_id = None
        db.session.commit()
        subscribe_url = url_for(
            "billing.subscribe",
            error="Could not verify subscription.",
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)

    status = status_result.get("status", "")

    if status.lower() in ["accepted", "active"]:
        try:
            store = (
                ShopifyStore.query.with_for_update()
                .filter_by(shop_url=shop_url, user_id=user.id)
                .first()
            )
            if not store:
                db.session.rollback()
                subscribe_url = url_for(
                    "billing.subscribe",
                    error="Store not found",
                    shop=shop,
                    host=host,
                    plan=plan_type,
                )
                return safe_redirect(subscribe_url, shop=shop, host=host)

            locked_access_token = store.get_access_token()
            if not locked_access_token:
                logger.error(f"No access token found for store {shop_url} during charge confirmation for user {user.id}")
                db.session.rollback()
                subscribe_url = url_for(
                    "billing.subscribe",
                    error="Store not properly connected",
                    shop=shop,
                    host=host,
                    plan=plan_type,
                )
                return safe_redirect(subscribe_url, shop=shop, host=host)

            activate_result = activate_recurring_charge(
                shop_url, locked_access_token, charge_id
            )

            if activate_result.get("success"):
                # Update user subscription status atomically
                try:
                    with db.session.begin():  # Use transaction
                        user.is_subscribed = True
                        store.charge_id = str(charge_id)
                        
                        # Always sync SubscriptionPlan
                        existing_plan = SubscriptionPlan.query.filter_by(user_id=user.id).first()
                        if existing_plan:
                            existing_plan.status = "active"
                            existing_plan.charge_id = str(charge_id)
                            existing_plan.cancelled_at = None
                            existing_plan.plan_type = plan_type
                            existing_plan.price_usd = PLAN_PRICES.get(plan_type, 39.00)
                        else:
                            new_plan = SubscriptionPlan(
                                user_id=user.id,
                                plan_type=plan_type,
                                price_usd=PLAN_PRICES.get(plan_type, 39.00),
                                charge_id=str(charge_id),
                                status="active",
                                multi_store_enabled=True,
                                automated_reports_enabled=True,
                                scheduled_delivery_enabled=True,
                            )
                            db.session.add(new_plan)
                        
                        logger.info(f"Subscription activated for {shop_url}, plan: {plan_type}")
                except Exception as e:
                    logger.error(f"Transaction failed: {e}")
                    raise

                # Set trial end date
                trial_end_date = datetime.utcnow() + timedelta(days=7)
                user.trial_ends_at = trial_end_date
                
                # Return enhanced success page
                dashboard_url = f"/dashboard?shop={shop_url}&host={host}&success=subscription_activated"
                
                return render_template_string(
                    SUCCESS_HTML, 
                    shop=shop_url, 
                    host=host,
                    trial_end_date=trial_end_date.strftime('%B %d, %Y'),
                    dashboard_url=dashboard_url
                )
            else:
                db.session.rollback()
                logger.error(f"Failed to activate charge for user {user.id}, shop {shop_url}: {activate_result.get('error')}")
                subscribe_url = url_for(
                    "billing.subscribe",
                    error="Failed to activate subscription",
                    shop=shop,
                    host=host,
                    plan=plan_type,
                )
                return safe_redirect(subscribe_url, shop=shop, host=host)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in charge activation for user {user.id}, shop {shop_url}: {e}", exc_info=True)
            subscribe_url = url_for(
                "billing.subscribe",
                error="Error processing subscription",
                shop=shop,
                host=host,
                plan=plan_type,
            )
            return safe_redirect(subscribe_url, shop=shop, host=host)

    elif status == "active":
        try:
            user.is_subscribed = True
            store.charge_id = str(charge_id)
            db.session.commit()
            logger.info(f"Subscription already active for {shop_url}, user: {user.id}")
            # Set trial end date
            trial_end_date = datetime.utcnow() + timedelta(days=7)
            user.trial_ends_at = trial_end_date
            
            # Return enhanced success page
            dashboard_url = f"/dashboard?shop={shop_url}&host={host}&success=subscription_activated"
            
            return render_template_string(
                SUCCESS_HTML, 
                shop=shop_url, 
                host=host,
                trial_end_date=trial_end_date.strftime('%B %d, %Y'),
                dashboard_url=dashboard_url
            )
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database error marking subscription active for user {user.id}, shop {shop_url}: {e}")
            subscribe_url = url_for(
                "billing.subscribe",
                error="Error processing subscription",
                shop=shop,
                host=host,
                plan=plan_type,
            )
            return safe_redirect(subscribe_url, shop=shop, host=host)

    elif status == "declined":
        logger.info(f"Merchant declined subscription for {shop_url}")
        subscribe_url = url_for(
            "billing.subscribe",
            error="Subscription was declined",
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)

    else:
        logger.warning(f"Unexpected charge status '{status}' for {shop_url}")
        subscribe_url = url_for(
            "billing.subscribe",
            error=f"Subscription status: {status}",
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)


@billing_bp.route("/billing/cancel", methods=["POST"])
def cancel_subscription():
    """Cancel Shopify subscription"""
    import requests

    shop = request.form.get("shop") or request.args.get("shop", "")
    host = request.form.get("host") or request.args.get("host", "")

    user = None
    try:
        if current_user.is_authenticated:
            user_id = current_user.get_id()
            if user_id:
                user = User.query.get(int(user_id))
        if not user and shop:
            store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
            if store and store.user:
                user = store.user
    except Exception:
        pass

    if not user:
        settings_url = url_for(
            "shopify.shopify_settings",
            error="Authentication required",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    if not store or not store.charge_id:
        settings_url = url_for(
            "shopify.shopify_settings",
            error="No active subscription found",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    url = f"https://{store.shop_url}/admin/api/{SHOPIFY_API_VERSION}/recurring_application_charges/{store.charge_id}.json"
    headers = {
        "X-Shopify-Access-Token": store.get_access_token() or "",
        "Content-Type": "application/json",
    }

    try:
        response = requests.delete(url, headers=headers, timeout=10)
        if response.status_code in [200, 404]:
            user.is_subscribed = False
            store.charge_id = None
            db.session.commit()
            logger.info(f"Subscription cancelled for {store.shop_url}")
            settings_url = url_for(
                "shopify.shopify_settings",
                success="Subscription cancelled",
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)
        else:
            logger.error(f"Failed to cancel subscription: {response.status_code}")
            settings_url = url_for(
                "shopify.shopify_settings",
                error="Failed to cancel subscription",
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        settings_url = url_for(
            "shopify.shopify_settings", error=str(e), shop=shop, host=host
        )
        return safe_redirect(settings_url, shop=shop, host=host)


@billing_bp.route("/test-billing", methods=["GET", "POST"])
def test_billing():
    return jsonify(
        {
            "message": "Billing blueprint is working",
            "method": request.method,
            "args": dict(request.args),
            "form": dict(request.form),
        }
    )


