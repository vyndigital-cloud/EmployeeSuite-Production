"""
Shopify Billing Integration
MANDATORY: All Shopify App Store apps MUST use Shopify Billing API
Stripe/external payment processors are NOT allowed for embedded apps
"""
from flask import Blueprint, render_template_string, request, redirect, url_for, session, Response
from flask_login import login_required, current_user
import os
from models import db, ShopifyStore, User
from datetime import datetime
from logging_config import logger

billing_bp = Blueprint('billing', __name__)

# Shopify Billing API configuration
SHOPIFY_API_VERSION = '2025-10'
APP_URL = os.getenv('SHOPIFY_APP_URL', 'https://employeesuite-production.onrender.com')

def safe_redirect(url, shop=None, host=None):
    """Safe redirect for embedded/standalone contexts - App Bridge compliant"""
    is_embedded = bool(host) or bool(shop) or request.args.get('embedded') == '1'
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
        return Response(redirect_html, mimetype='text/html')
    else:
        return redirect(url)

# Plan configuration
PLANS = {
    'pro': {'name': 'Growth', 'price': 29.00, 'features': [
        'Inventory Intelligence Dashboard',
        'Smart Reorder Recommendations',
        'Dead Stock Alerts',
        '30-Day Sales Forecasting',
        'CSV Export Capable',
        'Up to 3 Store Connections',
        'Email Support'
    ]},
    'business': {'name': 'Scale', 'price': 99.00, 'features': [
        'Everything in Growth',
        'Advanced Multi-Location Sync',
        'Automated Supplier Emails',
        'Custom Reporting Engine',
        'Unlimited Data History',
        'Priority 24/7 Support',
        'Dedicated Success Manager',
        'Early Access to Beta Features'
    ]}
}

SUBSCRIBE_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Upgrade to {{ plan_name }}</title>
    <!-- Shopify App Bridge -->
    <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
    <script>
        var apiKey = '{{ config_api_key }}'; // Injected by server if available
        var shopOrigin = '{{ shop }}';
        if (apiKey && shopOrigin) {
            var AppBridge = window['app-bridge'];
            var createApp = AppBridge.default;
            var app = createApp({
                apiKey: apiKey,
                shopOrigin: shopOrigin,
                forceRedirect: true
            });
        }
    </script>
    <style>
        :root {
            --p-color-bg-surface: #ffffff;
            --p-color-bg-app: #f1f2f4;
            --p-color-text: #202223;
            --p-color-text-subdued: #6d7175;
            --p-color-action-primary: #008060;
            --p-color-action-primary-hover: #006e52;
            --p-border-radius-base: 8px;
            --p-shadow-card: 0px 0px 5px rgba(23, 24, 24, 0.05), 0px 1px 2px rgba(0, 0, 0, 0.15);
            --p-font-family: -apple-system, BlinkMacSystemFont, "San Francisco", "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
        }

        body {
            font-family: var(--p-font-family);
            background-color: var(--p-color-bg-app);
            color: var(--p-color-text);
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
        }

        .layout {
            max-width: 900px;
            width: 100%;
            padding: 40px 20px;
            display: grid;
            grid-template-columns: 1fr 380px;
            gap: 40px;
            align-items: start;
        }

        /* Value Proposition Section (Left) */
        .value-prop {
            padding-top: 20px;
        }

        .back-link {
            display: inline-flex;
            align-items: center;
            color: var(--p-color-text-subdued);
            text-decoration: none;
            font-size: 14px;
            margin-bottom: 24px;
            font-weight: 500;
            transition: color 0.15s;
        }

        .back-link:hover {
            color: var(--p-color-action-primary);
        }

        .brand-pill {
            display: inline-block;
            background: #e3fcef;
            color: #006e52;
            font-weight: 600;
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 20px;
            margin-bottom: 16px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }

        h1 {
            font-size: 32px;
            font-weight: 700;
            margin: 0 0 12px 0;
            line-height: 1.2;
            color: #1a1a1a;
        }

        .subtitle {
            font-size: 16px;
            color: var(--p-color-text-subdued);
            line-height: 1.5;
            margin-bottom: 32px;
            max-width: 440px;
        }

        .feature-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
        }

        .feature-card {
            display: flex;
            gap: 16px;
        }

        .feature-icon {
            width: 40px;
            height: 40px;
            background: #ffffff;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            flex-shrink: 0;
        }

        .feature-content h3 {
            font-size: 15px;
            font-weight: 600;
            margin: 0 0 4px 0;
        }

        .feature-content p {
            font-size: 14px;
            color: var(--p-color-text-subdued);
            margin: 0;
            line-height: 1.5;
        }

        /* Checkout Card (Right) */
        .checkout-card {
            background: var(--p-color-bg-surface);
            border-radius: var(--p-border-radius-base);
            box-shadow: var(--p-shadow-card);
            overflow: hidden;
            position: sticky;
            top: 40px;
        }

        .card-header {
            padding: 24px 24px 20px;
            border-bottom: 1px solid #e1e3e5;
        }

        .plan-name {
            font-size: 13px;
            font-weight: 600;
            color: var(--p-color-text-subdued);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .price-container {
            display: flex;
            align-items: baseline;
            gap: 4px;
        }

        .price {
            font-size: 36px;
            font-weight: 700;
            color: var(--p-color-text);
        }

        .period {
            font-size: 14px;
            color: var(--p-color-text-subdued);
        }

        .card-body {
            padding: 24px;
        }

        .checklist {
            margin-bottom: 24px;
        }

        .check-item {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
            font-size: 14px;
            color: #374151;
        }

        .check-icon {
            color: var(--p-color-action-primary);
            flex-shrink: 0;
            width: 16px;
            height: 16px;
        }

        .check-item:last-child {
            margin-bottom: 0;
        }

        .btn-subscribe {
            display: block;
            width: 100%;
            background-color: var(--p-color-action-primary);
            color: white;
            padding: 14px;
            border: none;
            border-radius: 6px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s ease;
            box-shadow: 0 1px 0 rgba(0,0,0,0.05);
        }

        .btn-subscribe:hover {
            background-color: var(--p-color-action-primary-hover);
        }

        .btn-subscribe:disabled {
            background-color: #a8a8a8;
            cursor: not-allowed;
        }

        .guarantee-text {
            text-align: center;
            font-size: 12px;
            color: var(--p-color-text-subdued);
            margin-top: 16px;
            line-height: 1.4;
        }

        .error-banner {
            background: #fff5f5;
            border: 1px solid #fed7d7;
            color: #c53030;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 13px;
            line-height: 1.4;
        }

        /* Responsive */
        @media (max-width: 800px) {
            .layout {
                grid-template-columns: 1fr;
                gap: 32px;
                padding: 24px 16px;
            }
            .checkout-card {
                position: static;
                max-width: 500px;
                margin: 0 auto;
            }
        }
    </style>
</head>
<body>
    <div class="layout">
        <!-- Left Column: Value Proposition -->
        <div class="value-prop">
            <a href="/dashboard?shop={{ shop }}&host={{ host }}" class="back-link">
                <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor" style="margin-right: 4px;">
                    <path d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"/>
                </svg>
                Back to Dashboard
            </a>

            <div>
                <span class="brand-pill">Inventory Intelligence</span>
                <h1>Upgrade Your Store's Brain</h1>
                <p class="subtitle">
                    Stop guessing. Start knowing. Get purely data-driven insights to optimize stock, reduce waste, and maximize profit margins.
                </p>
            </div>

            <div class="feature-grid">
                <div class="feature-card">
                    <div class="feature-icon">🔍</div>
                    <div class="feature-content">
                        <h3>Dead Stock Detection</h3>
                        <p>Identify items that haven't sold in 60+ days but are tying up your capital.</p>
                    </div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📈</div>
                    <div class="feature-content">
                        <h3>Smart Forecasts</h3>
                        <p>Predict inventory needs based on real sales velocity, not just gut feeling.</p>
                    </div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">⚡</div>
                    <div class="feature-content">
                        <h3>Automated Alerts</h3>
                        <p>Get notified instantly when high-velocity items drop below safe levels.</p>
                    </div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📊</div>
                    <div class="feature-content">
                        <h3>Profit Analytics</h3>
                        <p>See true profitability per SKU, factoring in storage and holding costs.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Right Column: Checkout Card -->
        <div class="checkout-card">
            <div class="card-header">
                <div class="plan-name">{{ plan_name }} Plan</div>
                <div class="price-container">
                    <span class="price">${{ price }}</span>
                    <span class="period">/ month</span>
                </div>
            </div>
            
            <div class="card-body">
                {% if error %}
                    <div class="error-banner">
                        <strong>Something went wrong:</strong><br>
                        {{ error }}
                    </div>
                {% endif %}

                <div class="checklist">
                    {% for feature in features %}
                    <div class="check-item">
                        <svg class="check-icon" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        <span>{{ feature }}</span>
                    </div>
                    {% endfor %}
                </div>

                <form id="subscribe-form" method="POST" action="/billing/create-charge">
                    <input type="hidden" name="shop" value="{{ shop }}">
                    <input type="hidden" name="host" value="{{ host }}">
                    <input type="hidden" name="plan" value="{{ plan }}">
                    
                    <button type="submit" class="btn-subscribe" id="subscribe-btn" {% if not has_store %}disabled{% endif %}>
                        {% if not has_store %}
                            Connect Store First
                        {% else %}
                            Start 7-Day Free Trial
                        {% endif %}
                    </button>
                    
                    {% if not has_store %}
                    <div style="text-align: center; margin-top: 12px;">
                        <a href="/settings/shopify?shop={{ shop }}&host={{ host }}" style="font-size: 13px; color: #008060; text-decoration: none; font-weight: 500;">Connect Shopify Store &rarr;</a>
                    </div>
                    {% endif %}
                </form>

                <div class="guarantee-text">
                    <strong>7-day free trial.</strong><br>
                    You won't be charged until the trial ends.<br>
                    Cancel anytime via Shopify Admin.
                </div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('subscribe-form').addEventListener('submit', function(e) {
            var btn = document.getElementById('subscribe-btn');
            btn.disabled = true;
            btn.innerHTML = '<span style="display: inline-block; animation: spin 1s linear infinite; margin-right: 8px;">⟳</span> Processing...';
        });
    </script>
</body>
</html>
'''

SUCCESS_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Welcome - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="3;url=/dashboard?shop={{ shop }}&host={{ host }}">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f6f6f7;
            color: #202223;
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
            background: #e3fcef;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            margin: 0 auto 24px;
        }
        .success-title { font-size: 28px; font-weight: 600; color: #202223; margin-bottom: 12px; }
        .success-text { font-size: 16px; color: #6d7175; line-height: 1.6; margin-bottom: 24px; }
        .btn {
            padding: 12px 24px;
            background: #008060;
            color: #fff;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            display: inline-block;
        }
    </style>
</head>
<body>
    <div class="success-container">
        <div class="success-icon">✓</div>
        <h1 class="success-title">You're All Set!</h1>
        <p class="success-text">Your subscription is now active. You have full access to Employee Suite.</p>
        <a href="/dashboard?shop={{ shop }}&host={{ host }}" class="btn">Go to Dashboard</a>
    </div>
</body>
</html>
'''

def get_shop_and_token_for_user(user):
    """Get shop URL and access token for a user"""
    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    if store and store.is_connected():
        return store.shop_url, store.get_access_token()
    return None, None


def format_billing_error(error_msg):
    """Format billing error messages to be more user-friendly"""
    error_lower = error_msg.lower()

    if '422' in error_msg or 'unprocessable' in error_lower:
        if 'owned by a shop' in error_lower or 'must be migrated' in error_lower:
            return """App Migration Required

Your app needs to be migrated to the Shopify Partners area before billing can work.

To fix this:
1. Go to https://partners.shopify.com
2. Navigate to your app → Settings
3. Look for "App ownership" section
4. Migrate the app from Shop ownership to Partners ownership
5. Once migrated, try subscribing again"""
        elif 'managed pricing' in error_lower or 'pricing' in error_lower:
            return "Billing setup issue: Please check your app's pricing settings in the Shopify Partners dashboard."
        else:
            return f"Unable to create subscription. Error: {error_msg[:100]}"
    elif '403' in error_msg or 'forbidden' in error_lower:
        return "Permission denied: Your app may not have billing permissions."
    elif '401' in error_msg or 'unauthorized' in error_lower:
        return "Authentication error: Please try reconnecting your Shopify store."
    else:
        return f"Subscription error: {error_msg[:150]}"


def create_recurring_charge(shop_url, access_token, return_url, plan_type='pro'):
    """Create a recurring application charge using Shopify Billing API"""
    import requests

    plan = PLANS.get(plan_type, PLANS['pro'])

    url = f"https://{shop_url}/admin/api/{SHOPIFY_API_VERSION}/recurring_application_charges.json"
    headers = {
        'X-Shopify-Access-Token': access_token,
        'Content-Type': 'application/json'
    }

    is_dev_store = '-dev' in shop_url.lower() or 'dev' in shop_url.lower()
    test_mode = os.getenv('SHOPIFY_BILLING_TEST', 'false').lower() == 'true' or is_dev_store

    payload = {
        'recurring_application_charge': {
            'name': f"Employee Suite {plan['name']}",
            'price': plan['price'],
            'return_url': return_url,
            'trial_days': 7,
            'test': test_mode
        }
    }

    logger.info(f"Creating {plan_type} plan charge: ${plan['price']}/mo for {shop_url}")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)

        if not response.ok:
            try:
                error_data = response.json()
                if isinstance(error_data, dict):
                    error_message = error_data.get('errors', {})
                    if isinstance(error_message, dict):
                        error_message = error_message.get('base', [])
                    error_text = str(error_message) if error_message else response.text
                else:
                    error_text = str(error_data)
                logger.error(f"Shopify API error: {response.status_code} - {error_text}")
                return {'success': False, 'error': f"Shopify API error: {error_text}"}
            except (ValueError, KeyError, TypeError):
                return {'success': False, 'error': f"Shopify API error ({response.status_code})"}

        response.raise_for_status()
        data = response.json()
        charge = data.get('recurring_application_charge', {})

        return {
            'success': True,
            'charge_id': charge.get('id'),
            'confirmation_url': charge.get('confirmation_url'),
            'status': charge.get('status')
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create Shopify charge: {e}")
        return {'success': False, 'error': str(e)}


def activate_recurring_charge(shop_url, access_token, charge_id):
    """Activate a recurring charge after merchant approves"""
    import requests

    url = f"https://{shop_url}/admin/api/{SHOPIFY_API_VERSION}/recurring_application_charges/{charge_id}/activate.json"
    headers = {
        'X-Shopify-Access-Token': access_token,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        charge = data.get('recurring_application_charge', {})
        return {
            'success': True,
            'status': charge.get('status'),
            'activated_on': charge.get('activated_on')
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to activate Shopify charge: {e}")
        return {'success': False, 'error': str(e)}


def get_charge_status(shop_url, access_token, charge_id):
    """Get the status of a recurring charge"""
    import requests

    url = f"https://{shop_url}/admin/api/{SHOPIFY_API_VERSION}/recurring_application_charges/{charge_id}.json"
    headers = {
        'X-Shopify-Access-Token': access_token,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        charge = data.get('recurring_application_charge', {})
        return {
            'success': True,
            'status': charge.get('status'),
            'charge_id': charge.get('id')
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get Shopify charge status: {e}")
        return {'success': False, 'error': str(e)}


@billing_bp.route('/subscribe')
def subscribe():
    """Subscribe page - uses Shopify Billing API"""
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    plan_type = request.args.get('plan', 'pro')

    # Validate plan type
    if plan_type not in PLANS:
        plan_type = 'pro'

    plan = PLANS[plan_type]

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
        return render_template_string(SUBSCRIBE_HTML,
            trial_active=False, has_access=False, days_left=0,
            is_subscribed=False, shop=shop, host=host, has_store=False,
            plan=plan_type, plan_name=plan['name'], price=int(plan['price']),
            features=plan['features'],
            error='Please connect your Shopify store first.')

    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    has_store = store is not None and store.is_connected()

    if not shop and store:
        shop = store.shop_url

    trial_active = user.is_trial_active()
    has_access = user.has_access()
    days_left = (user.trial_ends_at - datetime.utcnow()).days if trial_active else 0

    error = request.args.get('error')
    if not has_store and not error:
        error = 'No Shopify store connected'

    return render_template_string(SUBSCRIBE_HTML,
        trial_active=trial_active, has_access=has_access, days_left=days_left,
        is_subscribed=user.is_subscribed, shop=shop, host=host, has_store=has_store,
        plan=plan_type, plan_name=plan['name'], price=int(plan['price']),
        features=plan['features'], error=error,
        config_api_key=os.getenv('SHOPIFY_API_KEY'))


@billing_bp.route('/billing/create-charge', methods=['POST'])
def create_charge():
    """Create a Shopify recurring charge"""
    shop = request.form.get('shop') or request.args.get('shop', '')
    host = request.form.get('host') or request.args.get('host', '')
    plan_type = request.form.get('plan') or request.args.get('plan', 'pro')

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
        subscribe_url = url_for('billing.subscribe', error='Please connect your Shopify store first.', shop=shop, host=host, plan=plan_type)
        return safe_redirect(subscribe_url, shop=shop, host=host)

    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    if not store:
        logger.error(f"No active store found for user {user.id}")
        subscribe_url = url_for('billing.subscribe', error='No Shopify store connected', shop=shop, host=host, plan=plan_type)
        return safe_redirect(subscribe_url, shop=shop, host=host)

    shop_url = store.shop_url

    if not store.is_connected():
        logger.error(f"Store {shop_url} not connected")
        settings_url = url_for('shopify.shopify_settings', error='Store not connected. Please reconnect.', shop=shop_url, host=host)
        return safe_redirect(settings_url, shop=shop_url, host=host)

    access_token = store.get_access_token()

    if user.is_subscribed:
        dashboard_url = f'/dashboard?shop={shop_url}&host={host}'
        return safe_redirect(dashboard_url, shop=shop_url, host=host)

    return_url = f"{APP_URL}/billing/confirm?shop={shop_url}&host={host}&plan={plan_type}"

    result = create_recurring_charge(shop_url, access_token, return_url, plan_type)

    if not result.get('success'):
        error_msg = result.get('error', 'Failed to create subscription')
        logger.error(f"Billing error for {shop_url}: {error_msg}")

        if 'owned by a shop' in error_msg.lower() or 'must be migrated' in error_msg.lower():
            store.disconnect()
            db.session.commit()
            install_url = url_for('oauth.install', shop=shop_url, host=host)
            return render_template_string(f"""
            <!DOCTYPE html>
            <html><head><meta charset="utf-8"><title>Redirecting...</title>
            <script>window.location.href = '{install_url}';</script>
            </head><body><p>Redirecting...</p></body></html>
            """)

        formatted_error = format_billing_error(error_msg)
        return redirect(url_for('billing.subscribe', error=formatted_error, shop=shop_url, host=host, plan=plan_type))

    store.charge_id = str(result['charge_id'])
    db.session.commit()

    logger.info(f"Created Shopify charge {result['charge_id']} for {shop_url}")

    confirmation_url = result['confirmation_url']
    if host:
        return safe_redirect(confirmation_url, shop=shop_url, host=host)
    else:
        return redirect(confirmation_url)


@billing_bp.route('/billing/confirm')
def confirm_charge():
    """Handle return from Shopify after merchant approves/declines charge"""
    from enhanced_models import SubscriptionPlan, PLAN_PRICES

    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    charge_id = request.args.get('charge_id')
    plan_type = request.args.get('plan', 'pro')

    if not charge_id:
        logger.warning("No charge_id in billing confirm callback")
        subscribe_url = url_for('billing.subscribe', error='Missing charge information', shop=shop, host=host, plan=plan_type)
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
        subscribe_url = url_for('billing.subscribe', error='Please connect your Shopify store first.', shop=shop, host=host, plan=plan_type)
        return safe_redirect(subscribe_url, shop=shop, host=host)

    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    if not store:
        subscribe_url = url_for('billing.subscribe', error='Store not found', shop=shop, host=host, plan=plan_type)
        return safe_redirect(subscribe_url, shop=shop, host=host)

    shop_url = store.shop_url
    access_token = store.get_access_token()
    if not access_token:
        subscribe_url = url_for('billing.subscribe', error='Store not properly connected.', shop=shop, host=host, plan=plan_type)
        return safe_redirect(subscribe_url, shop=shop, host=host)

    status_result = get_charge_status(shop_url, access_token, charge_id)

    if not status_result.get('success'):
        store.charge_id = None
        db.session.commit()
        subscribe_url = url_for('billing.subscribe', error='Could not verify subscription.', shop=shop, host=host, plan=plan_type)
        return safe_redirect(subscribe_url, shop=shop, host=host)

    status = status_result.get('status', '')

    if status == 'accepted':
        try:
            store = ShopifyStore.query.with_for_update().filter_by(shop_url=shop_url, user_id=user.id).first()
            if not store:
                db.session.rollback()
                subscribe_url = url_for('billing.subscribe', error='Store not found', shop=shop, host=host, plan=plan_type)
                return safe_redirect(subscribe_url, shop=shop, host=host)

            locked_access_token = store.get_access_token()
            if not locked_access_token:
                db.session.rollback()
                subscribe_url = url_for('billing.subscribe', error='Store not properly connected', shop=shop, host=host, plan=plan_type)
                return safe_redirect(subscribe_url, shop=shop, host=host)

            activate_result = activate_recurring_charge(shop_url, locked_access_token, charge_id)

            if activate_result.get('success'):
                user.is_subscribed = True
                store.charge_id = str(charge_id)

                # Create/update SubscriptionPlan
                plan_price = PLAN_PRICES.get(plan_type, 29.00)
                existing_plan = SubscriptionPlan.query.filter_by(user_id=user.id).first()
                if existing_plan:
                    existing_plan.plan_type = plan_type
                    existing_plan.price_usd = plan_price
                    existing_plan.charge_id = str(charge_id)
                    existing_plan.status = 'active'
                    existing_plan.cancelled_at = None
                    existing_plan.multi_store_enabled = (plan_type == 'business')
                    existing_plan.automated_reports_enabled = (plan_type == 'business')
                    existing_plan.scheduled_delivery_enabled = (plan_type == 'business')
                else:
                    new_plan = SubscriptionPlan(
                        user_id=user.id,
                        plan_type=plan_type,
                        price_usd=plan_price,
                        charge_id=str(charge_id),
                        status='active',
                        multi_store_enabled=(plan_type == 'business'),
                        automated_reports_enabled=(plan_type == 'business'),
                        scheduled_delivery_enabled=(plan_type == 'business'),
                    )
                    db.session.add(new_plan)

                db.session.commit()
                logger.info(f"Subscription activated for {shop_url}, plan: {plan_type}")

                return render_template_string(SUCCESS_HTML, shop=shop_url, host=host)
            else:
                db.session.rollback()
                logger.error(f"Failed to activate charge: {activate_result.get('error')}")
                subscribe_url = url_for('billing.subscribe', error='Failed to activate subscription', shop=shop, host=host, plan=plan_type)
                return safe_redirect(subscribe_url, shop=shop, host=host)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in charge activation: {e}")
            subscribe_url = url_for('billing.subscribe', error='Error processing subscription', shop=shop, host=host, plan=plan_type)
            return safe_redirect(subscribe_url, shop=shop, host=host)

    elif status == 'active':
        user.is_subscribed = True
        store.charge_id = str(charge_id)
        db.session.commit()
        return render_template_string(SUCCESS_HTML, shop=shop_url, host=host)

    elif status == 'declined':
        logger.info(f"Merchant declined subscription for {shop_url}")
        subscribe_url = url_for('billing.subscribe', error='Subscription was declined', shop=shop, host=host, plan=plan_type)
        return safe_redirect(subscribe_url, shop=shop, host=host)

    else:
        logger.warning(f"Unexpected charge status '{status}' for {shop_url}")
        subscribe_url = url_for('billing.subscribe', error=f'Subscription status: {status}', shop=shop, host=host, plan=plan_type)
        return safe_redirect(subscribe_url, shop=shop, host=host)


@billing_bp.route('/billing/cancel', methods=['POST'])
def cancel_subscription():
    """Cancel Shopify subscription"""
    import requests

    shop = request.form.get('shop') or request.args.get('shop', '')
    host = request.form.get('host') or request.args.get('host', '')

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
        settings_url = url_for('shopify.shopify_settings', error='Authentication required', shop=shop, host=host)
        return safe_redirect(settings_url, shop=shop, host=host)

    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    if not store or not store.charge_id:
        settings_url = url_for('shopify.shopify_settings', error='No active subscription found', shop=shop, host=host)
        return safe_redirect(settings_url, shop=shop, host=host)

    url = f"https://{store.shop_url}/admin/api/{SHOPIFY_API_VERSION}/recurring_application_charges/{store.charge_id}.json"
    headers = {
        'X-Shopify-Access-Token': store.get_access_token() or '',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.delete(url, headers=headers, timeout=10)
        if response.status_code in [200, 404]:
            user.is_subscribed = False
            store.charge_id = None
            db.session.commit()
            logger.info(f"Subscription cancelled for {store.shop_url}")
            settings_url = url_for('shopify.shopify_settings', success='Subscription cancelled', shop=shop, host=host)
            return safe_redirect(settings_url, shop=shop, host=host)
        else:
            logger.error(f"Failed to cancel subscription: {response.status_code}")
            settings_url = url_for('shopify.shopify_settings', error='Failed to cancel subscription', shop=shop, host=host)
            return safe_redirect(settings_url, shop=shop, host=host)
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        settings_url = url_for('shopify.shopify_settings', error=str(e), shop=shop, host=host)
        return safe_redirect(settings_url, shop=shop, host=host)


@billing_bp.route('/pricing')
def pricing_page():
    """Pricing page showing all plans"""
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')

    return render_template_string(PRICING_HTML, shop=shop, host=host)


PRICING_HTML = '''
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
        .logo { font-size: 16px; font-weight: 600; color: #202223; text-decoration: none; }
        .nav-btn { padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: 500; text-decoration: none; color: #6d7175; }
        .nav-btn:hover { background: #f6f6f7; color: #202223; }
        .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 48px 24px;
        }
        .page-header {
            text-align: center;
            margin-bottom: 48px;
        }
        .page-title {
            font-size: 32px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 12px;
        }
        .page-subtitle {
            font-size: 16px;
            color: #6d7175;
        }
        .trial-badge {
            display: inline-block;
            background: #e3fcef;
            color: #006e52;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
            margin-top: 16px;
        }
        .pricing-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 24px;
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
            border: 1px solid #e1e3e5;
            border-radius: 8px;
            padding: 32px 24px;
            display: flex;
            flex-direction: column;
        }
        .pricing-card.featured {
            border: 2px solid #008060;
            position: relative;
        }
        .popular-badge {
            position: absolute;
            top: -12px;
            left: 50%;
            transform: translateX(-50%);
            background: #008060;
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .plan-name {
            font-size: 20px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 8px;
        }
        .plan-desc {
            font-size: 14px;
            color: #6d7175;
            margin-bottom: 16px;
        }
        .plan-price {
            font-size: 42px;
            font-weight: 700;
            color: #202223;
            margin-bottom: 8px;
        }
        .plan-price span {
            font-size: 16px;
            font-weight: 500;
            color: #6d7175;
        }
        .plan-features {
            list-style: none;
            margin: 24px 0;
            flex-grow: 1;
        }
        .plan-features li {
            padding: 8px 0;
            font-size: 14px;
            color: #374151;
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }
        .plan-features li::before {
            content: "✓";
            color: #008060;
            font-weight: 600;
            flex-shrink: 0;
        }
        .plan-features li.disabled {
            color: #b5b5b5;
        }
        .plan-features li.disabled::before {
            content: "—";
            color: #b5b5b5;
        }
        .btn {
            display: block;
            width: 100%;
            padding: 12px 16px;
            text-align: center;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            font-size: 14px;
            transition: all 0.15s;
            border: none;
            cursor: pointer;
        }
        .btn-primary {
            background: #008060;
            color: white;
        }
        .btn-primary:hover {
            background: #006e52;
        }
        .btn-secondary {
            background: #f6f6f7;
            color: #202223;
            border: 1px solid #e1e3e5;
        }
        .btn-secondary:hover {
            background: #e1e3e5;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <a href="/dashboard?shop={{ shop }}&host={{ host }}" class="logo">Employee Suite</a>
            <a href="/dashboard?shop={{ shop }}&host={{ host }}" class="nav-btn">Back to Dashboard</a>
        </div>
    </div>

    <div class="container">
        <div class="page-header">
            <h1 class="page-title">Simple, Transparent Pricing</h1>
            <p class="page-subtitle">Choose the plan that's right for your business</p>
            <span class="trial-badge">7-day free trial on all paid plans</span>
        </div>

        <div class="pricing-grid">
            <!-- FREE Plan -->
            <div class="pricing-card">
                <div class="plan-name">Free</div>
                <div class="plan-desc">Get started with basics</div>
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
                </ul>
                <a href="/register" class="btn btn-secondary">Get Started Free</a>
            </div>

            <!-- PRO Plan -->
            <div class="pricing-card featured">
                <span class="popular-badge">Most Popular</span>
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
                </ul>
                <a href="/subscribe?plan=pro&shop={{ shop }}&host={{ host }}" class="btn btn-primary">Start Free Trial</a>
            </div>

            <!-- BUSINESS Plan -->
            <div class="pricing-card">
                <div class="plan-name">Business</div>
                <div class="plan-desc">For power users</div>
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
                </ul>
                <a href="/subscribe?plan=business&shop={{ shop }}&host={{ host }}" class="btn btn-primary">Start Free Trial</a>
            </div>
        </div>
    </div>
</body>
</html>
'''
