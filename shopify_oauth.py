import os
import hmac
import hashlib
import requests
from urllib.parse import quote, unquote
from flask import Blueprint, request, redirect, session
from models import db, ShopifyStore, User
from flask_login import login_user, current_user
from logging_config import logger

oauth_bp = Blueprint('oauth', __name__)

SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
SHOPIFY_API_SECRET = os.getenv('SHOPIFY_API_SECRET')
# App Store required scopes - only request what you need (Shopify requirement)
SCOPES = 'read_products,read_inventory,read_orders'
REDIRECT_URI = os.getenv('SHOPIFY_REDIRECT_URI', 'https://employeesuite-production.onrender.com/auth/callback')
# Access mode: offline = persistent token, online = session-based token
# Use offline for background operations (webhooks, cron jobs)
ACCESS_MODE = 'offline'

@oauth_bp.route('/install')
def install():
    """Initiate Shopify OAuth - Professional error handling"""
    shop = request.args.get('shop', '').strip()
    
    if not shop:
        from flask import render_template_string
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Install Employee Suite</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background: #f6f6f7;
                }
                .container {
                    text-align: center;
                    padding: 40px 24px;
                    max-width: 500px;
                }
                .title {
                    font-size: 18px;
                    font-weight: 600;
                    color: #202223;
                    margin-bottom: 12px;
                }
                .message {
                    font-size: 14px;
                    color: #6d7175;
                    line-height: 1.5;
                    margin-bottom: 24px;
                }
                .btn {
                    display: inline-block;
                    padding: 10px 20px;
                    background: #008060;
                    color: #fff;
                    border-radius: 6px;
                    text-decoration: none;
                    font-size: 14px;
                    font-weight: 500;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="title">Shop parameter required</div>
                <div class="message">Please install Employee Suite from your Shopify admin panel, or include your shop domain in the URL.</div>
                <a href="/settings/shopify" class="btn">Go to Settings</a>
            </div>
        </body>
        </html>
        """), 400
    
    # Normalize shop domain - add .myshopify.com if not present
    shop = shop.replace('https://', '').replace('http://', '').replace('www.', '')
    if not shop.endswith('.myshopify.com'):
        shop = f"{shop}.myshopify.com"
    
    # Build authorization URL
    # For App Store installations, Shopify will include 'host' parameter in callback
    # We store it in state to preserve it through OAuth flow
    host = request.args.get('host', '')
    state_data = shop
    if host:
        # Encode host in state for embedded app installations
        # Use a separator that won't conflict with shop domain
        state_data = f"{shop}||{quote(host, safe='')}"
    
    auth_url = f"https://{shop}/admin/oauth/authorize"
    params = {
        'client_id': SHOPIFY_API_KEY,
        'scope': SCOPES,
        'redirect_uri': REDIRECT_URI,  # Must match Partners Dashboard exactly - no query params
        'state': state_data,
        'grant_options[]': ACCESS_MODE  # Request offline (persistent) access token
    }
    
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    return redirect(f"{auth_url}?{query_string}")

@oauth_bp.route('/auth/callback')
def callback():
    """Handle Shopify OAuth callback"""
    shop = request.args.get('shop')
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not shop or not code:
        return "Missing required parameters", 400
    
    # Verify HMAC
    hmac_verified = verify_hmac(request.args)
    if not hmac_verified:
        return "HMAC verification failed", 403
    
    # Exchange code for access token
    # CRITICAL: Log which API key is being used for OAuth (for debugging)
    current_api_key = os.getenv('SHOPIFY_API_KEY', 'NOT_SET')
    if current_api_key and current_api_key != 'NOT_SET' and len(current_api_key) >= 8:
        logger.info(f"OAUTH DEBUG: Using API key for token exchange: {current_api_key[:8]}... (length: {len(current_api_key)})")
    else:
        logger.error(f"OAUTH DEBUG: API key is NOT SET or invalid! current_api_key={current_api_key}")
    logger.info(f"OAUTH DEBUG: Shop: {shop}")
    
    access_token = exchange_code_for_token(shop, code)
    
    if not access_token:
        return "Failed to get access token", 500
    
    logger.info(f"OAUTH DEBUG: Access token received: {access_token[:10]}... (first 10 chars)")
    logger.info(f"OAUTH DEBUG: This token is tied to API key: {current_api_key[:8]}...")
    
    # Get shop information to extract shop_id
    shop_info = get_shop_info(shop, access_token)
    shop_id = shop_info.get('id') if shop_info else None
    
    # Get or create user (for App Store, use shop domain as identifier)
    user = User.query.filter_by(email=f"{shop}@shopify.com").first()
    if not user:
        from datetime import datetime, timedelta
        user = User(
            email=f"{shop}@shopify.com",
            password_hash='',  # OAuth users don't have passwords
            trial_ends_at=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(user)
        db.session.commit()
    
    # CRITICAL: Log which API key was used to generate this access_token
    current_api_key = os.getenv('SHOPIFY_API_KEY', 'NOT_SET')
    if current_api_key and current_api_key != 'NOT_SET' and len(current_api_key) >= 8:
        api_key_preview = current_api_key[:8]
        logger.info(f"OAUTH COMPLETE: Generated new access_token using Partners API key: {api_key_preview}... (length: {len(current_api_key)})")
        logger.info(f"OAUTH COMPLETE: This access_token is tied to Partners app: {api_key_preview}...")
    else:
        logger.error(f"OAUTH COMPLETE: WARNING - API key is NOT SET or invalid! current_api_key={current_api_key}")
    
    # Store Shopify credentials with shop_id
    store = ShopifyStore.query.filter_by(shop_url=shop).first()
    if store:
        # CRITICAL: Always update access_token when reconnecting (gets new token from new Partners app)
        old_token_preview = store.access_token[:10] if store.access_token and len(store.access_token) > 10 else (store.access_token or "None")
        new_token_preview = access_token[:10] if len(access_token) > 10 else access_token
        store.access_token = access_token
        store.shop_id = shop_id
        store.is_active = True
        store.user_id = user.id
        logger.info(f"Updated existing store {shop} with new access_token (old: {old_token_preview}..., new: {new_token_preview}...)")
    else:
        store = ShopifyStore(
            user_id=user.id,
            shop_url=shop,
            shop_id=shop_id,
            access_token=access_token,
            is_active=True
        )
        db.session.add(store)
        token_preview = access_token[:10] if len(access_token) > 10 else access_token
        logger.info(f"Created new store {shop} with access_token: {token_preview}...")
    
    db.session.commit()
    
    # Register mandatory compliance webhooks (Shopify requirement)
    register_compliance_webhooks(shop, access_token)
    
    # Log user in - for OAuth (embedded apps), use session tokens, not remember cookies
    # Session tokens are primary auth for embedded apps, cookies are secondary
    is_embedded = bool(host)  # If host is present, this is embedded
    login_user(user, remember=not is_embedded)  # No remember cookie for embedded apps
    session.permanent = True
    session.modified = True  # Force immediate session save (Safari compatibility)
    
    if is_embedded:
        logger.info(f"OAuth login for embedded app (session token auth)")
    else:
        logger.info(f"OAuth login for standalone access (cookie auth)")
    
    # Handle redirect after OAuth - check if this is an embedded app (App Store installation)
    # Shopify sends 'host' parameter for embedded apps
    host = request.args.get('host')
    
    # Also check state for host (in case it was passed through from install endpoint)
    state = request.args.get('state', '')
    if state and '||' in state and not host:
        # State contains shop||host format
        parts = state.split('||', 1)
        if len(parts) == 2:
            host = unquote(parts[1])
    
    # If host is present, this is an embedded app installation (App Store)
    # CRITICAL: Use Shopify App Bridge for navigation within embedded apps
    # Regular redirects and window.top.location can cause "refused to connect" errors
    if host:
        app_url = os.getenv('SHOPIFY_APP_URL', 'https://employeesuite-production.onrender.com')
        api_key = os.getenv('SHOPIFY_API_KEY', '')
        embedded_url = f"{app_url}/dashboard?shop={shop}&host={host}&embedded=1"
        logger.info(f"OAuth complete for embedded app, redirecting to: {embedded_url}")
        
        # Professional OAuth redirect - matches Shopify's seamless flow
        redirect_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Employee Suite - Installation Complete</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
    <script>
        (function() {{
            var redirectAttempted = false;
            var maxAttempts = 3;
            var attemptCount = 0;
            
            function attemptRedirect() {{
                if (redirectAttempted || attemptCount >= maxAttempts) return;
                attemptCount++;
                
                try {{
                    var AppBridge = window['app-bridge'];
                    if (!AppBridge || !AppBridge.default) {{
                        if (attemptCount < maxAttempts) {{
                            setTimeout(attemptRedirect, 200);
                            return;
                        }}
                        // Final fallback
                        window.location.href = '{embedded_url}';
                        return;
                    }}
                    
                    var app = AppBridge.default({{
                        apiKey: '{api_key}',
                        host: '{host}'
                    }});
                    
                    var Redirect = AppBridge.actions.Redirect;
                    var redirect = Redirect.create(app);
                    
                    redirect.dispatch(Redirect.Action.APP, '/dashboard?shop={shop}&host={host}&embedded=1');
                    redirectAttempted = true;
                }} catch (e) {{
                    console.error('Redirect attempt ' + attemptCount + ' failed:', e);
                    if (attemptCount < maxAttempts) {{
                        setTimeout(attemptRedirect, 300);
                    }} else {{
                        // Final fallback after all attempts
                        window.location.href = '{embedded_url}';
                    }}
                }}
            }}
            
            // Start redirect immediately
            attemptRedirect();
            
            // Fallback timeout (3 seconds)
            setTimeout(function() {{
                if (!redirectAttempted) {{
                    window.location.href = '{embedded_url}';
                }}
            }}, 3000);
        }})();
    </script>
    <noscript>
        <meta http-equiv="refresh" content="0;url={embedded_url}">
    </noscript>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            background: #f6f6f7;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}
        .container {{
            text-align: center;
            padding: 40px 24px;
            max-width: 400px;
        }}
        .spinner {{
            width: 48px;
            height: 48px;
            border: 3px solid #e1e3e5;
            border-top-color: #008060;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 24px;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        .title {{
            font-size: 18px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 8px;
            letter-spacing: -0.2px;
        }}
        .message {{
            font-size: 14px;
            color: #6d7175;
            line-height: 1.5;
            margin-bottom: 24px;
        }}
        .fallback-link {{
            display: inline-block;
            font-size: 13px;
            color: #008060;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 6px;
            transition: background 0.15s;
        }}
        .fallback-link:hover {{
            background: #f0f4ff;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="spinner"></div>
        <div class="title">Setting up Employee Suite</div>
        <div class="message">Your store is being connected. You'll be redirected in a moment.</div>
        <a href="{embedded_url}" class="fallback-link">Continue to app →</a>
    </div>
</body>
</html>"""
        from flask import Response
        return Response(redirect_html, mimetype='text/html')
    
    # Non-embedded installation - regular redirect works fine
    return redirect('/dashboard')

def verify_hmac(params):
    """Verify Shopify HMAC"""
    hmac_to_verify = params.get('hmac')
    if not hmac_to_verify:
        return False
    
    # Create copy without hmac
    params_copy = dict(params)
    params_copy.pop('hmac', None)
    
    # Build query string
    query_string = '&'.join([f"{k}={v}" for k, v in sorted(params_copy.items())])
    
    # Calculate HMAC
    calculated_hmac = hmac.new(
        SHOPIFY_API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(calculated_hmac, hmac_to_verify)

def exchange_code_for_token(shop, code):
    """Exchange authorization code for access token"""
    url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        'client_id': SHOPIFY_API_KEY,
        'client_secret': SHOPIFY_API_SECRET,
        'code': code
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                return data.get('access_token') if isinstance(data, dict) else None
            except (ValueError, KeyError) as e:
                logger.error(f"Error parsing access token response: {e}")
                return None
        
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting access token: {e}")
        return None

def get_shop_info(shop, access_token):
    """Get shop information including shop_id"""
    url = f"https://{shop}/admin/api/2024-10/shop.json"
    headers = {
        'X-Shopify-Access-Token': access_token,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('shop', {})
    except Exception as e:
        logger.error(f"Failed to get shop info: {e}")
    
    return None

def register_compliance_webhooks(shop, access_token):
    """
    Register mandatory compliance webhooks via Admin API
    This ensures webhooks are registered even if shopify.app.toml isn't deployed via CLI
    """
    app_url = os.getenv('SHOPIFY_APP_URL', 'https://employeesuite-production.onrender.com')
    api_version = "2024-10"
    
    # Mandatory compliance webhooks
    webhooks = [
        {
            'topic': 'customers/data_request',
            'address': f'{app_url}/webhooks/customers/data_request',
            'format': 'json'
        },
        {
            'topic': 'customers/redact',
            'address': f'{app_url}/webhooks/customers/redact',
            'format': 'json'
        },
        {
            'topic': 'shop/redact',
            'address': f'{app_url}/webhooks/shop/redact',
            'format': 'json'
        }
    ]
    
    headers = {
        'X-Shopify-Access-Token': access_token,
        'Content-Type': 'application/json'
    }
    
    for webhook in webhooks:
        url = f"https://{shop}/admin/api/{api_version}/webhooks.json"
        payload = {'webhook': webhook}
        
        try:
            # Check if webhook already exists
            list_url = f"https://{shop}/admin/api/{api_version}/webhooks.json?topic={webhook['topic']}"
            list_response = requests.get(list_url, headers=headers, timeout=10)
            
            if list_response.status_code == 200:
                existing = list_response.json().get('webhooks', [])
                # Check if webhook with this address already exists
                exists = any(w.get('address') == webhook['address'] for w in existing)
                if exists:
                    continue  # Already registered, skip
            
            # Create webhook
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                logger.info(f"Successfully registered compliance webhook: {webhook['topic']} for shop {shop}")
            else:
                logger.warning(f"Failed to register webhook {webhook['topic']}: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error registering webhook {webhook['topic']}: {e}", exc_info=True)
