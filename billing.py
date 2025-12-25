"""
Shopify Billing Integration
MANDATORY: All Shopify App Store apps MUST use Shopify Billing API
Stripe/external payment processors are NOT allowed for embedded apps
"""
from flask import Blueprint, render_template_string, request, redirect, url_for, session, Response

def safe_redirect(url, shop=None, host=None):
    """
    Safe redirect that works in both embedded and standalone contexts.
    For embedded apps, uses window.top.location.href to break out of iframe.
    For standalone, uses regular Flask redirect.
    """
    # Check if we're in an embedded context
    is_embedded = bool(host) or bool(shop) or request.args.get('embedded') == '1'
    
    if is_embedded:
        # Embedded app - use window.top.location.href to break out of iframe
        redirect_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Redirecting...</title>
    <script>
        // Break out of iframe immediately
        if (window.top !== window.self) {{
            window.top.location.href = '{url}';
        }} else {{
            window.location.href = '{url}';
        }}
    </script>
    <noscript>
        <meta http-equiv="refresh" content="0;url={url}">
    </noscript>
</head>
<body>
    <p>Redirecting... <a href="{url}">Click here if not redirected</a></p>
</body>
</html>"""
        return Response(redirect_html, mimetype='text/html')
    else:
        # Standalone - use regular Flask redirect
        return redirect(url)
from flask_login import login_required, current_user
import os
from models import db, ShopifyStore, User
from datetime import datetime
from logging_config import logger

billing_bp = Blueprint('billing', __name__)

# Shopify Billing API configuration
SHOPIFY_API_VERSION = '2024-10'
APP_URL = os.getenv('SHOPIFY_APP_URL', 'https://employeesuite-production.onrender.com')

SUBSCRIBE_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Subscribe - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta charset="utf-8">
    <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
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
        .logo { font-size: 16px; font-weight: 600; color: #202223; text-decoration: none; }
        .nav-btn { padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: 500; text-decoration: none; color: #6d7175; }
        .nav-btn:hover { background: #f6f6f7; color: #202223; }
        .container { max-width: 600px; margin: 0 auto; padding: 32px 24px; }
        .page-title { font-size: 28px; font-weight: 600; color: #202223; margin-bottom: 8px; }
        .page-subtitle { font-size: 15px; color: #6d7175; margin-bottom: 32px; }
        .pricing-card { 
            background: #ffffff;
            border: 1px solid #e1e3e5;
            border-radius: 8px;
            padding: 32px;
        }
        .btn {
            width: 100%;
            padding: 12px 16px;
            background: #008060;
            color: #fff;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.15s;
        }
        .btn:hover { background: #006e52; }
        .btn:disabled { background: #8c9196; cursor: not-allowed; }
        .error-banner {
            background: #fff4f4;
            border: 1px solid #fecaca;
            border-left: 3px solid #d72c0d;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            color: #d72c0d;
            font-size: 14px;
        }
        .info-banner {
            background: #e3fcef;
            border: 1px solid #b2f5d1;
            border-left: 3px solid #008060;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            color: #006e52;
            font-size: 14px;
        }
        @media (max-width: 768px) {
            .container { padding: 24px 16px; }
            .page-title { font-size: 24px; }
            .pricing-card { padding: 24px; }
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
        <div style="text-align: center; margin-bottom: 40px;">
            <h1 class="page-title">{% if not has_access %}Restore Full Access{% else %}Premium Plan{% endif %}</h1>
            <p class="page-subtitle">
                {% if not has_access %}
                Your trial has ended. Subscribe to restore full access.
                {% elif trial_active and not is_subscribed %}
                Subscribe now to ensure uninterrupted access when your trial ends.
                {% else %}
                Get unlimited access to Employee Suite for $29/month.
                {% endif %}
            </p>
        </div>
        
        {% if error %}
        <div class="error-banner" style="white-space: pre-line;">{{ error }}</div>
        {% endif %}
        
        {% if not has_store %}
        <div class="error-banner" style="background: #fff4f4; border: 1px solid #fecaca; border-left: 3px solid #d72c0d; padding: 16px 20px;">
            <div style="font-weight: 600; color: #202223; margin-bottom: 8px; font-size: 15px;">⚠️ Connect Your Shopify Store First</div>
            <div style="color: #6d7175; font-size: 14px; margin-bottom: 16px; line-height: 1.5;">
                You need to connect your Shopify store before you can subscribe. This only takes 30 seconds.
            </div>
            <a href="/settings/shopify?shop={{ shop }}&host={{ host }}" style="display: inline-block; padding: 10px 20px; background: #008060; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px;">
                Connect Store →
            </a>
        </div>
        {% endif %}
        
        {% if trial_active and not is_subscribed %}
        <div class="info-banner">
            <strong>{{ days_left }} day{{ 's' if days_left != 1 else '' }} left in your trial</strong><br>
            Subscribe now to avoid interruption.
        </div>
        {% endif %}
        
        <div class="pricing-card">
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="font-size: 13px; font-weight: 600; text-transform: uppercase; color: #6d7175; margin-bottom: 12px;">Monthly Subscription</div>
                <div style="font-size: 48px; font-weight: 700; color: #202223; margin-bottom: 8px;">$29<span style="font-size: 20px; font-weight: 500; color: #6d7175;">/month</span></div>
                <div style="font-size: 14px; color: #6d7175;">7-day free trial • Cancel anytime</div>
            </div>
            
            <div style="background: #f6f6f7; border-radius: 8px; padding: 24px; margin-bottom: 24px;">
                <div style="font-size: 16px; font-weight: 600; color: #202223; margin-bottom: 16px;">Everything included:</div>
                <div style="display: flex; flex-direction: column; gap: 12px;">
                    <div style="display: flex; align-items: center; gap: 12px; font-size: 14px;">
                        <span style="color: #008060; font-weight: 600;">✓</span>
                        <span>Order Monitoring & Tracking</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px; font-size: 14px;">
                        <span style="color: #008060; font-weight: 600;">✓</span>
                        <span>Inventory Management with Low Stock Alerts</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px; font-size: 14px;">
                        <span style="color: #008060; font-weight: 600;">✓</span>
                        <span>Revenue Analytics & Reporting</span>
                    </div>
                </div>
            </div>
            
            <form id="subscribe-form" method="POST" action="/billing/create-charge">
                <input type="hidden" name="shop" value="{{ shop }}">
                <input type="hidden" name="host" value="{{ host }}">
                <button type="submit" class="btn" id="subscribe-btn" {% if not has_store %}disabled{% endif %}>
                    {% if not has_store %}
                        Connect Store to Subscribe
                    {% elif not has_access %}
                        Restore Access Now
                    {% else %}
                        Subscribe Now
                    {% endif %}
                </button>
            </form>
            
            {% if not has_store %}
            <p style="text-align: center; font-size: 13px; color: #6d7175; margin-top: 12px;">
                Click the button above to connect your store, then return here to subscribe.
            </p>
            {% else %}
            <p style="text-align: center; font-size: 12px; color: #6d7175; margin-top: 16px;">
                Billed through your Shopify account. Cancel anytime from your Shopify admin.
            </p>
            {% endif %}
            
    </div>
    
    <script>
        // Prevent double-submit
        document.getElementById('subscribe-form').addEventListener('submit', function(e) {
            var btn = document.getElementById('subscribe-btn');
            btn.disabled = true;
            btn.textContent = 'Redirecting to Shopify...';
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
    <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
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
        .btn:hover { background: #006e52; }
    </style>
</head>
<body>
    <div class="success-container">
        <div class="success-icon">✓</div>
        <h1 class="success-title">You're All Set!</h1>
        <p class="success-text">Your subscription is now active. You have full access to Employee Suite.</p>
        <a href="/dashboard?shop={{ shop }}&host={{ host }}" class="btn">Go to Dashboard</a>
    </div>
    
    <script>
        // Use App Bridge for navigation if available
        var urlParams = new URLSearchParams(window.location.search);
        var host = urlParams.get('host') || '{{ host }}';
        var apiKey = '{{ api_key }}';
        
        if (host && apiKey && window['app-bridge']) {
            var AppBridge = window['app-bridge'];
            var app = AppBridge.default({ apiKey: apiKey, host: host });
            var Redirect = AppBridge.actions.Redirect;
            var redirect = Redirect.create(app);
            
            setTimeout(function() {
                redirect.dispatch(Redirect.Action.APP, '/dashboard?shop={{ shop }}&host={{ host }}');
            }, 2000);
        }
    </script>
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
    """
    Format billing error messages to be more user-friendly
    Provides guidance for common issues
    """
    error_lower = error_msg.lower()
    
    # Check for common error patterns
    if '422' in error_msg or 'unprocessable' in error_lower:
        # Check for app ownership/migration errors - multiple variations
        ownership_keywords = [
            'owned by a shop',
            'owned by a Shop',
            'migrated to the shopify partners',
            'migrated to the Shopify Partners',
            'must be migrated',
            'currently owned by a Shop',
            'It appears that this application is currently owned by a Shop'
        ]
        if any(keyword in error_lower for keyword in ownership_keywords):
            return """⚠️ App Migration Required

Your app needs to be migrated to the Shopify Partners area before billing can work.

**To fix this:**
1. Go to https://partners.shopify.com
2. Navigate to your app → Settings
3. Look for "App ownership" or "Migration" section
4. Migrate the app from Shop ownership to Partners ownership
5. Once migrated, try subscribing again

This is a one-time setup required for all Shopify apps to use billing."""
        elif 'managed pricing' in error_lower or 'pricing' in error_lower:
            return "Billing setup issue: Please check your app's pricing settings in the Shopify Partners dashboard. Make sure 'Manual Pricing' is enabled (not 'Managed Pricing')."
        elif 'custom app' in error_lower:
            return "Billing setup issue: Your app needs to be a public app in the Shopify Partners area. Please verify your app configuration in the Partners dashboard."
        else:
            return f"Unable to create subscription. This may be due to app configuration. Please contact support if this persists. Error: {error_msg[:100]}"
    elif '403' in error_msg or 'forbidden' in error_lower:
        return "Permission denied: Your app may not have billing permissions. Please verify your app is properly configured in the Shopify Partners dashboard."
    elif '401' in error_msg or 'unauthorized' in error_lower:
        return "Authentication error: Please try reconnecting your Shopify store."
    else:
        return f"Subscription error: {error_msg[:150]}"


def create_recurring_charge(shop_url, access_token, return_url):
    """
    Create a recurring application charge using Shopify Billing API
    This is MANDATORY for Shopify App Store apps
    """
    import requests
    # #region agent log
    import json
    try:
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"billing.py:343","message":"Create recurring charge start","data":{"shop_url":shop_url,"has_token":bool(access_token),"return_url":return_url},"timestamp":int(__import__('time').time()*1000)})+'\n')
    except: pass
    # #endregion
    url = f"https://{shop_url}/admin/api/{SHOPIFY_API_VERSION}/recurring_application_charges.json"
    headers = {
        'X-Shopify-Access-Token': access_token,
        'Content-Type': 'application/json'
    }
    
    # Automatically enable test mode for development stores
    is_dev_store = shop_url.endswith('.myshopify.com') and ('-dev' in shop_url or 'dev' in shop_url.lower())
    test_mode = os.getenv('SHOPIFY_BILLING_TEST', 'false').lower() == 'true' or is_dev_store
    
    payload = {
        'recurring_application_charge': {
            'name': 'Employee Suite Pro',
            'price': 29.00,
            'return_url': return_url,
            'trial_days': 7,
            'test': test_mode
        }
    }
    
    if test_mode:
        logger.info(f"Using test mode for charge creation (dev store: {is_dev_store})")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        # #region agent log
        try:
            with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"billing.py:374","message":"Billing API response","data":{"status_code":response.status_code,"has_response":bool(response.text)},"timestamp":int(__import__('time').time()*1000)})+'\n')
        except: pass
        # #endregion
        # Log request details for debugging
        logger.info(f"Creating charge for {shop_url}, status: {response.status_code}")
        
        # If error, capture the actual response body
        if not response.ok:
            # #region agent log
            try:
                with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"billing.py:380","message":"Billing API error","data":{"status_code":response.status_code,"response_text":response.text[:300]},"timestamp":int(__import__('time').time()*1000)})+'\n')
            except: pass
            # #endregion
            try:
                error_data = response.json()
                # CRITICAL: Handle both dict and string error_data
                if isinstance(error_data, dict):
                    error_message = error_data.get('errors', {})
                    if isinstance(error_message, dict):
                        error_message = error_message.get('base', [])
                    if not error_message:
                        error_message = error_data.get('errors', 'Unknown error')
                    error_text = str(error_message) if error_message else response.text
                elif isinstance(error_data, str):
                    error_text = error_data
                else:
                    error_text = str(error_data) if error_data else response.text
                logger.error(f"Shopify API error for {shop_url}: {response.status_code} - {error_text}")
                logger.error(f"Response body: {response.text}")
                return {'success': False, 'error': f"Shopify API error: {error_text}"}
            except (ValueError, KeyError, TypeError):
                # If response isn't JSON or parsing fails, use the text
                logger.error(f"Shopify API error for {shop_url}: {response.status_code} - {response.text}")
                return {'success': False, 'error': f"Shopify API error ({response.status_code}): {response.text[:200]}"}
        
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
        error_msg = str(e)
        # Try to get response if available
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                # CRITICAL: Handle both dict and string error_data
                if isinstance(error_data, dict):
                    error_message = error_data.get('errors', {})
                    if isinstance(error_message, dict):
                        error_message = error_message.get('base', [])
                    if not error_message:
                        error_message = error_data.get('errors', 'Unknown error')
                    error_msg = f"{error_msg} - {error_message}"
                elif isinstance(error_data, str):
                    error_msg = f"{error_msg} - {error_data}"
                else:
                    error_msg = f"{error_msg} - {str(error_data)}"
                logger.error(f"Response body: {e.response.text}")
            except (ValueError, AttributeError, TypeError):
                if hasattr(e.response, 'text'):
                    error_msg = f"{error_msg} - {e.response.text[:200]}"
        
        logger.error(f"Failed to create Shopify charge for {shop_url}: {error_msg}")
        return {'success': False, 'error': error_msg}


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
    # Get shop context
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    
    # For embedded apps, check if there's a shop parameter and try to find user from store
    # For standalone, use Flask-Login
    user = None
    try:
        if current_user.is_authenticated:
            user = current_user
        elif shop:
            # Try to find user from shop (for embedded apps)
            store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
            if store and store.user:
                user = store.user
    except Exception:
        pass
    
    # If no user found, show message about needing to connect store
    if not user:
        return render_template_string(SUBSCRIBE_HTML, 
                                     trial_active=False, 
                                     has_access=False,
                                     days_left=0,
                                     is_subscribed=False,
                                     shop=shop,
                                     host=host,
                                     has_store=False,
                                     error='Please connect your Shopify store first to subscribe.')
    
    # Check if user has a connected store
    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    has_store = store is not None and store.is_connected()
    
    # If no shop param, try to get from user's store
    if not shop and store:
        shop = store.shop_url
    
    trial_active = user.is_trial_active()
    has_access = user.has_access()
    days_left = (user.trial_ends_at - datetime.utcnow()).days if trial_active else 0
    
    # Get error from query params, but override with store connection error if needed
    error = request.args.get('error')
    if not has_store and not error:
        error = 'No Shopify store connected'
    
    return render_template_string(SUBSCRIBE_HTML, 
                                 trial_active=trial_active, 
                                 has_access=has_access,
                                 days_left=days_left,
                                 is_subscribed=user.is_subscribed,
                                 shop=shop,
                                 host=host,
                                 has_store=has_store,
                                 error=error)


@billing_bp.route('/billing/create-charge', methods=['POST'])
def create_charge():
    """
    Create a Shopify recurring charge
    Redirects merchant to Shopify's payment approval page
    """
    # #region agent log
    import json
    try:
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"billing.py:551","message":"Create charge called","data":{"method":request.method,"has_shop_form":"shop" in request.form,"has_host_form":"host" in request.form,"shop":request.form.get('shop') or request.args.get('shop',''),"host":request.form.get('host') or request.args.get('host','')},"timestamp":int(__import__('time').time()*1000)})+'\n')
    except: pass
    # #endregion
    shop = request.form.get('shop') or request.args.get('shop', '')
    host = request.form.get('host') or request.args.get('host', '')
    
    # For embedded apps, try to find user from shop parameter
    # For standalone, use Flask-Login
    user = None
    try:
        if current_user.is_authenticated:
            user = current_user
        elif shop:
            # Try to find user from shop (for embedded apps)
            store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
            if store and store.user:
                user = store.user
    except Exception:
        pass
    
    if not user:
        # #region agent log
        try:
            with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"billing.py:574","message":"No user found for create charge","data":{"shop":shop},"timestamp":int(__import__('time').time()*1000)})+'\n')
        except: pass
        # #endregion
        subscribe_url = url_for('billing.subscribe', error='Please connect your Shopify store first to subscribe.', shop=shop, host=host)
        return safe_redirect(subscribe_url, shop=shop, host=host)
    
    # Get store credentials
    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    if not store:
        # #region agent log
        try:
            with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"billing.py:579","message":"No store found for user","data":{"user_id":user.id},"timestamp":int(__import__('time').time()*1000)})+'\n')
        except: pass
        # #endregion
        logger.error(f"No active store found for user {user.id}")
        subscribe_url = url_for('billing.subscribe', error='No Shopify store connected', shop=shop, host=host)
        return safe_redirect(subscribe_url, shop=shop, host=host)
    
    shop_url = store.shop_url
    
    # Use model method to check connection status
    if not store.is_connected():
        # #region agent log
        try:
            with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"billing.py:586","message":"Store not connected","data":{"shop_url":shop_url},"timestamp":int(__import__('time').time()*1000)})+'\n')
        except: pass
        # #endregion
        logger.error(f"No valid access_token found for store {shop_url} - user must reconnect")
        settings_url = url_for('shopify.shopify_settings', 
                              error='Store not connected. Please reconnect your store.',
                              shop=shop_url, host=host)
        return safe_redirect(settings_url, shop=shop_url, host=host)
    
    access_token = store.get_access_token()
    # #region agent log
    try:
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"billing.py:592","message":"Store found, creating charge","data":{"shop_url":shop_url,"has_token":bool(access_token)},"timestamp":int(__import__('time').time()*1000)})+'\n')
    except: pass
    # #endregion
    
    # CRITICAL: Log which API key is being used for OAuth (for debugging)
    current_api_key = os.getenv('SHOPIFY_API_KEY', 'NOT_SET')
    logger.info(f"BILLING DEBUG: Using API key: {current_api_key[:8] if len(current_api_key) > 8 else current_api_key}... (first 8 chars)")
    logger.info(f"BILLING DEBUG: Store: {shop_url}, Access token: {access_token[:10] if len(access_token) > 10 else access_token}... (first 10 chars)")
    logger.info(f"BILLING DEBUG: Access token was created by OAuth using API key: {current_api_key[:8] if len(current_api_key) > 8 else current_api_key}...")
    
    # Check if already subscribed
    if user.is_subscribed:
        dashboard_url = f'/dashboard?shop={shop_url}&host={host}'
        return safe_redirect(dashboard_url, shop=shop_url, host=host)
    
    # Build return URL for after Shopify approval
    return_url = f"{APP_URL}/billing/confirm?shop={shop_url}&host={host}"
    
    # Create recurring charge via Shopify Billing API
    result = create_recurring_charge(shop_url, access_token, return_url)
    # #region agent log
    try:
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"billing.py:608","message":"Charge creation result","data":{"success":result.get('success'),"has_error":"error" in result,"error":result.get('error','')[:200] if "error" in result else ""},"timestamp":int(__import__('time').time()*1000)})+'\n')
    except: pass
    # #endregion
    if not result.get('success'):
        error_msg = result.get('error', 'Failed to create subscription')
        logger.error(f"Billing error for {shop_url}: {error_msg}")
        
        # CRITICAL: If "app owned by a shop" error, clear the access_token and redirect to OAuth
        if 'owned by a shop' in error_msg.lower() or 'must be migrated' in error_msg.lower():
            logger.warning(f"Detected old app access_token for {shop_url} - clearing token and redirecting to OAuth")
            # Use model method for consistent state management
            store.disconnect()
            db.session.commit()
            logger.info(f"Cleared access_token for {shop_url} - redirecting to OAuth install to get new token")
            
            # CRITICAL: Never use server-side redirect() - it causes iframe to load accounts.shopify.com
            # Use client-side redirect by rendering HTML that loads the install route
            install_url = url_for('oauth.install', shop=shop_url, host=host) if host else url_for('oauth.install', shop=shop_url)
            logger.info(f"Redirecting {shop_url} to OAuth install via install route: {install_url}")
            from flask import render_template_string
            return render_template_string(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Redirecting...</title>
                <script>
                    window.location.href = '{install_url}';
                </script>
            </head>
            <body>
                <p>Redirecting...</p>
            </body>
            </html>
            """)
        
        # Format error message for better user experience
        formatted_error = format_billing_error(error_msg)
        return redirect(url_for('billing.subscribe', error=formatted_error, shop=shop_url, host=host))
    
    # Store charge_id for later confirmation
    store.charge_id = str(result['charge_id'])
    db.session.commit()
    
    logger.info(f"Created Shopify charge {result['charge_id']} for {shop_url}")
    
    # Redirect to Shopify's payment approval page
    # Merchant will approve/decline, then Shopify redirects back to return_url
    confirmation_url = result['confirmation_url']
    # For embedded apps, use safe_redirect to break out of iframe
    # Shopify's confirmation URL is external, so we need to break out of iframe first
    if host:
        # Embedded mode - use safe_redirect to break out of iframe before going to Shopify
        return safe_redirect(confirmation_url, shop=shop_url, host=host)
    else:
        # Standalone - regular redirect works
        return redirect(confirmation_url)


@billing_bp.route('/billing/confirm')
def confirm_charge():
    """
    Handle return from Shopify after merchant approves/declines charge
    Shopify adds charge_id to the return URL
    """
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    charge_id = request.args.get('charge_id')
    
    if not charge_id:
        logger.warning("No charge_id in billing confirm callback")
        subscribe_url = url_for('billing.subscribe', error='Missing charge information', shop=shop, host=host)
        return safe_redirect(subscribe_url, shop=shop, host=host)
    
    # For embedded apps, try to find user from shop parameter
    # For standalone, use Flask-Login
    user = None
    try:
        if current_user.is_authenticated:
            user = current_user
        elif shop:
            # Try to find user from shop (for embedded apps)
            store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
            if store and store.user:
                user = store.user
    except Exception:
        pass
    
    if not user:
        subscribe_url = url_for('billing.subscribe', error='Please connect your Shopify store first to subscribe.', shop=shop, host=host)
        return safe_redirect(subscribe_url, shop=shop, host=host)
    
    # Get store credentials
    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    if not store:
        subscribe_url = url_for('billing.subscribe', error='Store not found', shop=shop, host=host)
        return safe_redirect(subscribe_url, shop=shop, host=host)
    
    shop_url = store.shop_url
    access_token = store.access_token
    
    # Check charge status
    status_result = get_charge_status(shop_url, access_token, charge_id)
    
    if not status_result.get('success'):
        subscribe_url = url_for('billing.subscribe', error='Could not verify subscription', shop=shop, host=host)
        return safe_redirect(subscribe_url, shop=shop, host=host)
    
    status = status_result.get('status', '')
    
    if status == 'accepted':
        # Merchant approved - activate the charge
        activate_result = activate_recurring_charge(shop_url, access_token, charge_id)
        
        if activate_result.get('success'):
            # Update user subscription status
            user.is_subscribed = True
            store.charge_id = str(charge_id)
            db.session.commit()
            
            logger.info(f"Subscription activated for {shop_url}, charge_id: {charge_id}")
            
            # Show success page
            return render_template_string(SUCCESS_HTML, 
                                         shop=shop_url, 
                                         host=host,
                                         api_key=os.getenv('SHOPIFY_API_KEY', ''))
        else:
            logger.error(f"Failed to activate charge for {shop_url}: {activate_result.get('error')}")
            subscribe_url = url_for('billing.subscribe', error='Failed to activate subscription', shop=shop, host=host)
            return safe_redirect(subscribe_url, shop=shop, host=host)
    
    elif status == 'active':
        # Already active
        user.is_subscribed = True
        store.charge_id = str(charge_id)
        db.session.commit()
        
        return render_template_string(SUCCESS_HTML, 
                                     shop=shop_url, 
                                     host=host,
                                     api_key=os.getenv('SHOPIFY_API_KEY', ''))
    
    elif status == 'declined':
        logger.info(f"Merchant declined subscription for {shop_url}")
        subscribe_url = url_for('billing.subscribe', error='Subscription was declined', shop=shop, host=host)
        return safe_redirect(subscribe_url, shop=shop, host=host)
    
    else:
        # Pending or other status
        logger.warning(f"Unexpected charge status '{status}' for {shop_url}")
        subscribe_url = url_for('billing.subscribe', error=f'Subscription status: {status}', shop=shop, host=host)
        return safe_redirect(subscribe_url, shop=shop, host=host)


@billing_bp.route('/billing/cancel', methods=['POST'])
def cancel_subscription():
    """Cancel Shopify subscription - works in both embedded and standalone modes"""
    import requests
    
    shop = request.form.get('shop') or request.args.get('shop', '')
    host = request.form.get('host') or request.args.get('host', '')
    
    # Get authenticated user (works for both embedded and standalone)
    user = None
    try:
        if current_user.is_authenticated:
            user = current_user
        elif shop:
            # Try to find user from shop (for embedded apps)
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
    
    # Cancel via Shopify API
    url = f"https://{store.shop_url}/admin/api/{SHOPIFY_API_VERSION}/recurring_application_charges/{store.charge_id}.json"
    headers = {
        'X-Shopify-Access-Token': store.access_token,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.delete(url, headers=headers, timeout=10)
        # 200 or 404 both mean success (404 = already cancelled)
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


# Legacy routes for backwards compatibility (redirect to new flow)
@billing_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def legacy_checkout():
    """Legacy Stripe route - redirect to Shopify billing"""
    shop = request.form.get('shop') or ''
    host = request.form.get('host') or ''
    
    # Get shop from user's store if not provided
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    if store and not shop:
        shop = store.shop_url
    
    charge_url = url_for('billing.create_charge', shop=shop, host=host)
    return safe_redirect(charge_url, shop=shop, host=host)


@billing_bp.route('/success')
@login_required
def legacy_success():
    """Legacy success route - redirect to billing confirm"""
    return redirect(url_for('billing.subscribe'))
