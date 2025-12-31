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

# CRITICAL: Validate API credentials are set
if not SHOPIFY_API_KEY:
    logger.error("❌ CRITICAL: SHOPIFY_API_KEY environment variable is not set! OAuth will fail.")
if not SHOPIFY_API_SECRET:
    logger.error("❌ CRITICAL: SHOPIFY_API_SECRET environment variable is not set! OAuth will fail.")

# App Store required scopes - only request what you need (Shopify requirement)
# CRITICAL: These scopes MUST be enabled in Shopify Partners Dashboard → App Setup → Access Scopes
# If you get 403 errors, verify these scopes are CHECKED in Partners Dashboard
# The order doesn't matter, but ALL of these must be requested and granted
SCOPES = 'read_orders,read_products,read_inventory'  # read_orders FIRST to ensure it's included
# CRITICAL: Shopify only allows ONE redirect URI in Partners Dashboard
# We MUST always use the production URL: https://employeesuite-production.onrender.com/auth/callback
# Even when running locally, OAuth callbacks will go to production, then you can test locally after OAuth completes
# This is the standard approach since Shopify doesn't support multiple redirect URIs
REDIRECT_URI = os.getenv('SHOPIFY_REDIRECT_URI', 'https://employeesuite-production.onrender.com/auth/callback')
# Access mode: offline = persistent token, online = session-based token
# Use offline for background operations (webhooks, cron jobs)
ACCESS_MODE = 'offline'

@oauth_bp.route('/install')
def install():
    """Initiate Shopify OAuth - Professional error handling"""
    # #region agent log
    try:
        import json
        import time
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"OAUTH","location":"shopify_oauth.py:33","message":"OAuth install route accessed","data":{"has_shop":bool(request.args.get('shop')),"has_host":bool(request.args.get('host')),"has_api_key":bool(SHOPIFY_API_KEY),"has_api_secret":bool(SHOPIFY_API_SECRET)},"timestamp":int(time.time()*1000)})+'\n')
    except: pass
    # #endregion
    # CRITICAL: Check API credentials before proceeding
    if not SHOPIFY_API_KEY or not SHOPIFY_API_SECRET:
        from flask import render_template_string
        logger.error("OAuth install failed: Missing API credentials")
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Configuration Error - Employee Suite</title>
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
                .error-icon {
                    font-size: 48px;
                    margin-bottom: 16px;
                }
                .title {
                    font-size: 18px;
                    font-weight: 600;
                    color: #d72c0d;
                    margin-bottom: 12px;
                }
                .message {
                    font-size: 14px;
                    color: #6d7175;
                    line-height: 1.5;
                    margin-bottom: 24px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">⚠️</div>
                <div class="title">Configuration Error</div>
                <div class="message">SHOPIFY_API_KEY or SHOPIFY_API_SECRET is not set. Please check your deployment environment variables.</div>
            </div>
        </body>
        </html>
        """), 500
    
    shop = request.args.get('shop', '').strip()
    # #region agent log
    import json
    try:
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"I","location":"shopify_oauth.py:86","message":"Install route called","data":{"shop":shop,"has_shop":bool(shop),"has_api_key":bool(SHOPIFY_API_KEY),"has_api_secret":bool(SHOPIFY_API_SECRET),"redirect_uri":REDIRECT_URI},"timestamp":int(__import__('time').time()*1000)})+'\n')
    except: pass
    # #endregion
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
    
    # CRITICAL: Also check Referer header to detect embedded context if host param is missing
    # This handles cases where other routes redirect to /install without passing host
    if not host:
        referer = request.headers.get('Referer', '')
        if referer:
            from urllib.parse import urlparse, parse_qs
            try:
                parsed = urlparse(referer)
                query_params = parse_qs(parsed.query)
                if 'host' in query_params:
                    host = query_params['host'][0]
                    logger.info(f"Detected embedded context from Referer header, host: {host[:20]}...")
            except Exception as e:
                logger.debug(f"Could not parse host from Referer: {e}")
    
    state_data = shop
    if host:
        # Encode host in state for embedded app installations
        # Use a separator that won't conflict with shop domain
        state_data = f"{shop}||{quote(host, safe='')}"
    
    auth_url = f"https://{shop}/admin/oauth/authorize"
    
    # CRITICAL: Ensure ALL required scopes are included
    # These scopes MUST match what's configured in shopify.app.toml and Partners Dashboard
    required_scopes = [
        'read_orders',      # Required for orders API (prevents 403 errors)
        'read_products',    # Required for products API
        'read_inventory',   # Required for inventory API
    ]
    
    # Use explicit scope list to ensure read_orders is always included
    scopes_string = ','.join(required_scopes)
    
    # Verify read_orders is in the scopes
    if 'read_orders' not in scopes_string:
        logger.error(f"❌ CRITICAL: read_orders scope is MISSING from scopes list!")
        logger.error(f"Current scopes: {scopes_string}")
        # Force add it if missing
        if 'read_orders' not in SCOPES:
            scopes_string = f"{SCOPES},read_orders"
            logger.warning(f"⚠️ Added read_orders to scopes: {scopes_string}")
    else:
        logger.info(f"✅ Verified: read_orders is included in scopes")
    
    params = {
        'client_id': SHOPIFY_API_KEY,
        'scope': scopes_string,  # Use explicit scopes list
        'redirect_uri': REDIRECT_URI,  # Must match Partners Dashboard exactly - no query params
        'state': state_data
        # Modern OAuth flow: grant_options[] removed - access mode configured in Partners Dashboard
        # Dashboard shows "Use legacy install flow: false" - using modern flow
    }
    
    # CRITICAL: URL-encode all parameter values, especially redirect_uri
    # Shopify requires exact match, but values must be properly encoded in the query string
    # Log the redirect URI being used for debugging
    logger.info(f"OAuth install: Using redirect_uri={REDIRECT_URI} (must match Partners Dashboard exactly)")
    logger.info(f"OAuth install: Requesting scopes: {scopes_string}")
    logger.info(f"OAuth install: Scope breakdown - read_orders: {'read_orders' in scopes_string}, read_products: {'read_products' in scopes_string}, read_inventory: {'read_inventory' in scopes_string}")
    # #region agent log
    try:
        import json
        import time
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"shopify_oauth.py:198","message":"OAuth scope request","data":{"requested_scopes":SCOPES,"shop":shop,"api_key_preview":SHOPIFY_API_KEY[:8] if SHOPIFY_API_KEY else None},"timestamp":int(time.time()*1000)})+'\n')
    except: pass
    # #endregion
    # #region agent log
    try:
        import json
        import time
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"I","location":"shopify_oauth.py:202","message":"OAuth URL generated","data":{"redirect_uri":REDIRECT_URI,"shop":shop,"auth_url":auth_url},"timestamp":int(time.time()*1000)})+'\n')
    except: pass
    # #endregion
    
    query_string = '&'.join([f"{k}={quote(str(v), safe='')}" for k, v in params.items()])
    full_auth_url = f"{auth_url}?{query_string}"
    
    # Log the full OAuth URL (without sensitive data) for debugging
    logger.debug(f"OAuth install: Generated auth URL for shop {shop}")
    # Log scope parameter to verify it's in the URL
    scope_in_url = f"scope={quote(SCOPES, safe='')}" in query_string
    logger.info(f"OAuth install: Scope parameter in URL: {scope_in_url}")
    if not scope_in_url:
        logger.error(f"❌ CRITICAL: Scope parameter missing from OAuth URL! Query string: {query_string[:200]}")
    else:
        logger.info(f"✅ OAuth install: Scope parameter correctly included in URL")
    
    # CRITICAL: Also check if we're being accessed from admin.shopify.com (embedded context)
    # Even if host param is missing, if Referer is from admin.shopify.com, we're in an iframe
    is_embedded = bool(host)
    if not is_embedded:
        referer = request.headers.get('Referer', '')
        if referer and ('admin.shopify.com' in referer or 'myshopify.com' in referer):
            # Likely embedded - try to extract host from referer or use a default
            # If we can't get host, we'll use window.top.location.href fallback
            is_embedded = True
            logger.info(f"Detected embedded context from Referer: {referer[:50]}...")
    
    # SIMPLEST SOLUTION: If embedded, show a link that opens in new window
    # No JavaScript, no redirects, no App Bridge complexity - just a simple link
    # This avoids ALL iframe loading issues
    if is_embedded:
        # If we have host, use it. Otherwise, try to extract from Referer or use fallback
        if not host:
            # Try one more time to extract from Referer URL params
            referer = request.headers.get('Referer', '')
            if referer:
                from urllib.parse import urlparse, parse_qs
                try:
                    parsed = urlparse(referer)
                    query_params = parse_qs(parsed.query)
                    if 'host' in query_params:
                        host = query_params['host'][0]
                        logger.info(f"Extracted host from Referer: {host[:20]}...")
                except Exception:
                    pass
        
        logger.info(f"Embedded OAuth install detected for {shop}, showing link to open OAuth in new window")
        
        # SIMPLEST FIX: Just show a link that opens in a new window
        # No JavaScript redirects, no App Bridge complexity - just works
        from flask import render_template_string
        return render_template_string(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Connect Shopify Store - Employee Suite</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background: #f6f6f7;
                }}
                .container {{
                    text-align: center;
                    padding: 40px 24px;
                    max-width: 500px;
                    background: #fff;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                h1 {{
                    font-size: 20px;
                    font-weight: 600;
                    color: #202223;
                    margin-bottom: 16px;
                }}
                p {{
                    font-size: 14px;
                    color: #6d7175;
                    line-height: 1.5;
                    margin-bottom: 24px;
                }}
                .btn {{
                    display: inline-block;
                    background: #008060;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 500;
                    font-size: 14px;
                    transition: background 0.2s;
                }}
                .btn:hover {{
                    background: #006e52;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Connect Your Shopify Store</h1>
                <p>Click the button below to authorize the connection. This will open in a new window.</p>
                <a href="{full_auth_url}" target="_blank" class="btn">Continue to Shopify Authorization →</a>
            </div>
        </body>
        </html>
        """)
    
    # Non-embedded: regular redirect works fine
    return redirect(full_auth_url)
@oauth_bp.route('/auth/callback')
def callback():
    """Handle Shopify OAuth callback"""
    # #region agent log
    try:
        import json
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"M","location":"shopify_oauth.py:320","message":"OAuth callback entry","data":{"shop":request.args.get('shop',''),"code":bool(request.args.get('code')),"state":request.args.get('state',''),"host":request.args.get('host',''),"full_url":request.url,"referer":request.headers.get('Referer',''),"user_agent":request.headers.get('User-Agent','')[:100]},"timestamp":int(__import__('time').time()*1000)})+'\n')
    except: pass
    # #endregion
    # CRITICAL: Check API credentials before proceeding
    if not SHOPIFY_API_KEY or not SHOPIFY_API_SECRET:
        logger.error("OAuth callback failed: Missing API credentials")
        return "Configuration error: API credentials not set", 500
    
    shop = request.args.get('shop')
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not shop or not code:
        logger.error(f"OAuth callback failed: Missing parameters - shop={bool(shop)}, code={bool(code)}")
        return "Missing required parameters", 400
    
    # Verify HMAC
    hmac_verified = verify_hmac(request.args)
    if not hmac_verified:
        logger.error("OAuth callback failed: HMAC verification failed")
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
    
    # Check if user is already logged in (e.g., manually connecting from settings page)
    # If logged in, use their account; otherwise create/find shop-based user for App Store installs
    user = None
    try:
        if current_user.is_authenticated:
            user = current_user
            logger.info(f"OAuth callback: Using existing logged-in user {user.email} (ID: {user.id})")
    except Exception:
        # current_user not loaded yet or not authenticated - will create/find shop-based user
        pass
    
    if not user:
        # No logged-in user - this is likely an App Store installation
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
            logger.info(f"OAuth callback: Created new shop-based user {user.email} (ID: {user.id})")
        else:
            logger.info(f"OAuth callback: Found existing shop-based user {user.email} (ID: {user.id})")
    
    # CRITICAL: Log which API key was used to generate this access_token
    current_api_key = os.getenv('SHOPIFY_API_KEY', 'NOT_SET')
    if current_api_key and current_api_key != 'NOT_SET' and len(current_api_key) >= 8:
        api_key_preview = current_api_key[:8]
        logger.info(f"OAUTH COMPLETE: Generated new access_token using Partners API key: {api_key_preview}... (length: {len(current_api_key)})")
        logger.info(f"OAUTH COMPLETE: This access_token is tied to Partners app: {api_key_preview}...")
    else:
        logger.error(f"OAUTH COMPLETE: WARNING - API key is NOT SET or invalid! current_api_key={current_api_key}")
    
    # Store Shopify credentials with shop_id
    # CRITICAL: Find store by shop_url AND user_id to ensure we update the correct store
    # This prevents updating stores owned by different users
    store = ShopifyStore.query.filter_by(shop_url=shop, user_id=user.id).first()
    if not store:
        # If not found with user_id, check if store exists for this shop (might be from old flow)
        store = ShopifyStore.query.filter_by(shop_url=shop).first()
    
    if store:
        # CRITICAL: Always update access_token when reconnecting (gets new token from new Partners app)
        # Encrypt the token before storing
        from data_encryption import encrypt_access_token
        encrypted_token = encrypt_access_token(access_token)
        old_token_preview = store.access_token[:10] if store.access_token and len(store.access_token) > 10 else (store.access_token or "None")
        new_token_preview = access_token[:10] if len(access_token) > 10 else access_token
        old_user_id = store.user_id
        store.access_token = encrypted_token
        store.shop_id = shop_id
        store.is_active = True
        store.user_id = user.id  # Ensure it's linked to the correct user
        logger.info(f"Updated existing store {shop} with new OAuth access_token (old: {old_token_preview}..., new: {new_token_preview}..., old_user_id: {old_user_id}, new_user_id: {user.id})")
    else:
        # Encrypt the token before storing
        from data_encryption import encrypt_access_token
        encrypted_token = encrypt_access_token(access_token)
        store = ShopifyStore(
            user_id=user.id,
            shop_url=shop,
            shop_id=shop_id,
            access_token=encrypted_token,
            is_active=True
        )
        db.session.add(store)
        token_preview = access_token[:10] if len(access_token) > 10 else access_token
        logger.info(f"Created new store {shop} with OAuth access_token: {token_preview}... for user {user.id}")
    
    db.session.commit()
    
    # Register mandatory compliance webhooks (Shopify requirement)
    register_compliance_webhooks(shop, access_token)
    
    # Handle redirect after OAuth - check if this is an embedded app (App Store installation)
    # Shopify sends 'host' parameter for embedded apps
    # Extract host BEFORE using it for login logic
    host = request.args.get('host')
    
    # Also check state for host (in case it was passed through from install endpoint)
    state = request.args.get('state', '')
    if state and '||' in state and not host:
        # State contains shop||host format
        parts = state.split('||', 1)
        if len(parts) == 2:
            host = unquote(parts[1])
    
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
    
    # If host is present, this is an embedded app installation (App Store)
    # SIMPLEST FIX: Use window.top.location.href to break out of iframe
    # This is the ONLY reliable way to redirect in embedded apps
    if host:
        app_url = os.getenv('SHOPIFY_APP_URL', 'https://employeesuite-production.onrender.com')
        # Redirect to settings page with success message so user sees confirmation
        from flask import url_for
        from urllib.parse import quote
        
        # CRITICAL: Properly encode URL parameters to prevent "couldn't load page" errors
        # Build URL manually to ensure proper encoding
        base_url = f"{app_url}/settings/shopify"
        params = []
        params.append(f"success={quote('Store connected successfully!')}")
        params.append(f"shop={quote(shop)}")
        params.append(f"host={quote(host)}")
        redirect_url = f"{base_url}?{'&'.join(params)}"
        
        logger.info(f"OAuth complete for embedded app, redirecting to: {redirect_url}")
        # #region agent log
        try:
            import json
            with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"N","location":"shopify_oauth.py:468","message":"OAuth redirect using top.location","data":{"has_host":bool(host),"host":host[:50] if host else "","shop":shop,"redirect_url":redirect_url},"timestamp":int(__import__('time').time()*1000)})+'\n')
        except: pass
        # #endregion
        
        # ENHANCED: Multiple redirect attempts with error handling
        # This prevents "couldn't load page" errors by trying multiple methods
        import json as json_module
        redirect_url_json = json_module.dumps(redirect_url)
        redirect_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Redirecting...</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            background: #f6f6f7;
            text-align: center;
        }}
        .container {{
            padding: 40px 24px;
            max-width: 500px;
        }}
        .spinner {{
            border: 3px solid #e1e3e5;
            border-top: 3px solid #008060;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        .message {{
            font-size: 14px;
            color: #6d7175;
            margin-bottom: 20px;
        }}
        .btn {{
            display: inline-block;
            padding: 10px 20px;
            background: #008060;
            color: #fff;
            border-radius: 6px;
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
        }}
    </style>
    <script>
        var redirectUrl = {redirect_url_json};
        var attempts = 0;
        var maxAttempts = 3;
        
        function tryRedirect() {{
            attempts++;
            console.log('Redirect attempt', attempts, 'to:', redirectUrl);
            
            try {{
                // Method 1: Try window.top.location.href (breaks out of iframe)
                if (window.top !== window.self) {{
                    window.top.location.href = redirectUrl;
                }} else {{
                    window.location.href = redirectUrl;
                }}
                
                // If redirect doesn't happen within 2 seconds, try next method
                setTimeout(function() {{
                    if (attempts < maxAttempts) {{
                        // Method 2: Try window.location.replace (more reliable)
                        try {{
                            if (window.top !== window.self) {{
                                window.top.location.replace(redirectUrl);
                            }} else {{
                                window.location.replace(redirectUrl);
                            }}
                        }} catch (e) {{
                            console.error('Redirect method 2 failed:', e);
                            if (attempts < maxAttempts) {{
                                // Method 3: Show manual link
                                document.getElementById('manual-link').style.display = 'block';
                                document.getElementById('spinner').style.display = 'none';
                            }}
                        }}
                    }} else {{
                        // All attempts failed - show manual link
                        document.getElementById('manual-link').style.display = 'block';
                        document.getElementById('spinner').style.display = 'none';
                    }}
                }}, 2000);
            }} catch (e) {{
                console.error('Redirect failed:', e);
                // Show manual link on error
                document.getElementById('manual-link').style.display = 'block';
                document.getElementById('spinner').style.display = 'none';
            }}
        }}
        
        // Start redirect immediately
        tryRedirect();
        
        // Fallback: Also try on page load
        window.addEventListener('load', function() {{
            if (attempts === 0) {{
                tryRedirect();
            }}
        }});
    </script>
    <noscript>
        <meta http-equiv="refresh" content="0;url={redirect_url}">
    </noscript>
</head>
<body>
    <div class="container">
        <div id="spinner" class="spinner"></div>
        <div class="message">Connecting your store...</div>
        <div id="manual-link" style="display: none;">
            <p style="font-size: 14px; color: #6d7175; margin-bottom: 16px;">If you're not redirected automatically, click below:</p>
            <a href="{redirect_url}" class="btn">Continue to Settings →</a>
        </div>
    </div>
</body>
</html>"""
        from flask import Response
        import json
        return Response(redirect_html, mimetype='text/html')
    
    # Non-embedded installation - regular redirect works fine
    # #region agent log
    try:
        import json
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"M","location":"shopify_oauth.py:620","message":"OAuth non-embedded redirect","data":{"shop":shop,"has_host":False,"redirect_to":"/dashboard"},"timestamp":int(__import__('time').time()*1000)})+'\n')
    except: pass
    # #endregion
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
                access_token = data.get('access_token') if isinstance(data, dict) else None
                granted_scopes = data.get('scope', '') if isinstance(data, dict) else ''
                # #region agent log
                try:
                    import json
                    import time
                    with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"shopify_oauth.py:564","message":"OAuth token exchange success","data":{"shop":shop,"requested_scopes":SCOPES,"granted_scopes":granted_scopes,"scopes_match":granted_scopes == SCOPES or set(granted_scopes.split(',')) == set(SCOPES.split(','))},"timestamp":int(time.time()*1000)})+'\n')
                except: pass
                # #endregion
                if access_token:
                    logger.info(f"OAuth token exchange: Requested scopes: {SCOPES}")
                    logger.info(f"OAuth token exchange: Granted scopes: {granted_scopes}")
                    # Check if scopes match (order doesn't matter)
                    requested_set = set([s.strip() for s in SCOPES.split(',')])
                    granted_set = set([s.strip() for s in granted_scopes.split(',')]) if granted_scopes else set()
                    if requested_set != granted_set:
                        missing = requested_set - granted_set
                        extra = granted_set - requested_set
                        logger.error(f"⚠️ SCOPE MISMATCH: Requested {SCOPES} but got {granted_scopes}")
                        if missing:
                            logger.error(f"⚠️ MISSING SCOPES: {missing}")
                            logger.error(f"❌ CRITICAL: Missing scopes will cause 403 errors on API calls!")
                            logger.error(f"❌ ACTION REQUIRED: Go to Shopify Partners Dashboard → Your App → API permissions")
                            logger.error(f"❌ Ensure these scopes are CHECKED: {', '.join(missing)}")
                        if extra:
                            logger.warning(f"⚠️ EXTRA SCOPES: {extra}")
                    else:
                        logger.info(f"✅ Scopes match: {granted_scopes}")
                return access_token
            except (ValueError, KeyError) as e:
                logger.error(f"Error parsing access token response: {e}")
                return None
        
        # #region agent log
        try:
            import json
            import time
            with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"shopify_oauth.py:572","message":"OAuth token exchange failed","data":{"shop":shop,"status_code":response.status_code,"response_text":response.text[:200] if hasattr(response, 'text') else None},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting access token: {e}")
        # #region agent log
        try:
            import json
            import time
            with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"shopify_oauth.py:575","message":"OAuth token exchange exception","data":{"shop":shop,"error":str(e)[:200]},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        return None

def get_shop_info(shop, access_token):
    """Get shop information including shop_id"""
    url = f"https://{shop}/admin/api/2025-10/shop.json"
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
    api_version = "2025-10"
    
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
            elif response.status_code == 404:
                # GDPR compliance webhooks must be registered in Partners Dashboard, not via Admin API
                # This is expected for Partner apps - webhooks are already configured in app manifest
                logger.debug(f"Compliance webhook {webhook['topic']} not available via Admin API (expected for Partner apps - register in Partners Dashboard)")
            else:
                logger.warning(f"Failed to register webhook {webhook['topic']}: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error registering webhook {webhook['topic']}: {e}", exc_info=True)

