import hashlib
import hmac
import os
import base64
from urllib.parse import quote, unquote

import requests
from flask import Blueprint, current_app, redirect, render_template, request, session
from flask_login import current_user, login_user

from config import SHOPIFY_API_VERSION, config
from logging_config import logger
from models import ShopifyStore, User, db

oauth_bp = Blueprint("oauth", __name__, url_prefix="")

SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")

# CRITICAL: Validate API credentials are set
if not SHOPIFY_API_KEY:
    logger.error(
        "❌ CRITICAL: SHOPIFY_API_KEY environment variable is not set! OAuth will fail."
    )
if not SHOPIFY_API_SECRET:
    logger.error(
        "❌ CRITICAL: SHOPIFY_API_SECRET environment variable is not set! OAuth will fail."
    )

# App Store required scopes - only request what you need (Shopify requirement)
# CRITICAL: These scopes MUST be enabled in Shopify Partners Dashboard → App Setup → Access Scopes
# If you get 403 errors, verify these scopes are CHECKED in Partners Dashboard
# The order doesn't matter, but ALL of these must be requested and granted
SCOPES = "read_orders,read_products,read_inventory"  # GraphQL API doesn't need read_all_orders
# CRITICAL: Shopify only allows ONE redirect URI in Partners Dashboard
# We MUST always use the production URL: https://employeesuite-production.onrender.com/auth/callback
# Even when running locally, OAuth callbacks will go to production, then you can test locally after OAuth completes
# This is the standard approach since Shopify doesn't support multiple redirect URIs
REDIRECT_URI = (
    os.getenv(
        "SHOPIFY_REDIRECT_URI",
        "https://employeesuite-production.onrender.com/oauth/auth/callback",
    )
    .strip()
    .strip('"')
    .strip("'")
)
# Access mode: offline = persistent token, online = session-based token
# Use offline for background operations (webhooks, cron jobs)
ACCESS_MODE = "offline"


@oauth_bp.route("/install")
@oauth_bp.route(
    "/oauth/install"
)  # Alternative route for compatibility with settings page
def install():
    """Initiate Shopify OAuth - Professional error handling"""

    # DEBUGGING: Log all request details
    logger.info("=== OAUTH INSTALL DEBUG START ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request args: {dict(request.args)}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request referrer: {request.referrer}")
    logger.info(f"Request remote_addr: {request.remote_addr}")
    logger.info(f"Session data: {dict(session)}")

    # DEBUGGING: Check environment variables
    logger.info(f"SHOPIFY_API_KEY set: {bool(SHOPIFY_API_KEY)}")
    logger.info(f"SHOPIFY_API_SECRET set: {bool(SHOPIFY_API_SECRET)}")
    logger.info(f"REDIRECT_URI: {REDIRECT_URI}")

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

    shop = request.args.get("shop", "").strip()
    if not shop or shop == "None":
        shop = session.get("shop", "")
        
    logger.info(f"📥 OAuth Install: Initial shop parameter: '{shop}'")

    if not shop:
        logger.error("❌ OAuth Install FAILED: Missing shop domain")
        return "Error: Missing shop domain. Please open the app from your Shopify Admin.", 400

    # Normalize shop domain - professional consistent normalization
    # [SANITY] Strip any recursive state fragments that might have nested (e.g. from retries)
    original_shop = request.args.get('shop')
    shop = (
        shop.lower()
        .split('|')[0] # Remove any existing nonce fragments
        .split('||')[0] # Remove any existing host fragments
        .replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .strip()
    )

    # Validate shop domain before proceeding
    if "onrender.com" in shop or "employeesuite" in shop:
        logger.error(f"❌ OAuth Install FAILED: Invalid shop domain detected")
        logger.error(f"   - User entered: '{original_shop}'")
        logger.error(f"   - After normalization: '{shop}'")
        logger.error(
            f"   - This appears to be the app's own domain, not a Shopify store!"
        )
        return redirect(
            "/settings/shopify?error=Invalid shop domain. Please enter your Shopify store domain (e.g., yourstore.myshopify.com), not your app URL."
        )

    if not shop.endswith(".myshopify.com") and "." not in shop:
        shop = f"{shop}.myshopify.com"
        logger.info(f"🔧 Auto-added .myshopify.com suffix: {shop}")

    logger.info(f"✅ Normalized install shop: '{original_shop}' → '{shop}'")

    # Build authorization URL
    # For App Store installations, Shopify will include 'host' parameter in callback
    # We store it in state to preserve it through OAuth flow
    host = request.args.get("host", "")

    # CRITICAL: Also check Referer header to detect embedded context if host param is missing
    # This handles cases where other routes redirect to /install without passing host
    if not host:
        referer = request.headers.get("Referer", "")
        if referer:
            from urllib.parse import parse_qs, urlparse

            try:
                parsed = urlparse(referer)
                query_params = parse_qs(parsed.query)
                if "host" in query_params:
                    host = query_params["host"][0]
                    logger.info(
                        f"Detected embedded context from Referer header, host: {host[:20]}..."
                    )
            except Exception as e:
                logger.debug(f"Could not parse host from Referer: {e}")

    # [SECURITY] Implement State Nonce to prevent CSRF
    import secrets
    # [HYGIENE] Clear previous nonce before setting new one
    session.pop("shopify_nonce", None)
    nonce = secrets.token_hex(16)
    session["shopify_nonce"] = nonce

    state_data = f"{shop}|{nonce}" # Using single pipe as internal separator
    if host:
        # Include host if present, separate from shop|nonce
        state_data = f"{state_data}||{quote(host, safe='')}"

    auth_url = f"https://{shop}/admin/oauth/authorize"

    # CRITICAL: Ensure ALL required scopes are included
    # These scopes MUST match what's configured in shopify.app.toml and Partners Dashboard
    required_scopes = [
        "read_orders",  # Required for orders (GraphQL works without read_all_orders)
        "read_products",  # Required for products API
        "read_inventory",  # Required for inventory API
    ]

    # Use explicit scope list to ensure read_orders is always included
    scopes_string = ",".join(required_scopes)

    # Verify read_orders is in the scopes
    if "read_orders" not in scopes_string:
        logger.error(f"❌ CRITICAL: read_orders scope is MISSING from scopes list!")
        logger.error(f"Current scopes: {scopes_string}")
        # Force add it if missing
        if "read_orders" not in SCOPES:
            scopes_string = f"{SCOPES},read_orders"
            logger.warning(f"⚠️ Added read_orders to scopes: {scopes_string}")
    else:
        logger.info(f"✅ Verified: read_orders is included in scopes")

    params = {
        "client_id": SHOPIFY_API_KEY,
        "scope": scopes_string,  # Use explicit scopes list
        "redirect_uri": REDIRECT_URI.strip().strip('"').strip("'"),  # Clean URI
        "state": state_data,
        # Modern OAuth flow: grant_options[] removed - access mode configured in Partners Dashboard
        # Dashboard shows "Use legacy install flow: false" - using modern flow
    }

    # CRITICAL: URL-encode all parameter values, especially redirect_uri
    # Shopify requires exact match, but values must be properly encoded in the query string
    # Log the redirect URI being used for debugging
    logger.info(
        f"OAuth install: Using redirect_uri={REDIRECT_URI} (must match Partners Dashboard exactly)"
    )
    logger.info(f"OAuth install: Requesting scopes: {scopes_string}")
    logger.info(
        f"OAuth install: Scope breakdown - read_orders: {'read_orders' in scopes_string}, read_products: {'read_products' in scopes_string}, read_inventory: {'read_inventory' in scopes_string}"
    )

    query_string = "&".join(
        [f"{k}={quote(str(v), safe='')}" for k, v in params.items()]
    )
    full_auth_url = f"{auth_url}?{query_string}"

    # Log the full OAuth URL (without sensitive data) for debugging
    logger.info(f"🔗 OAuth install: Generated auth URL for shop {shop}")
    logger.info(f"   - Target: {auth_url}")
    logger.info(f"   - Redirect URI: {REDIRECT_URI}")
    logger.info(f"   - State: {state_data}")

    # Log scope parameter to verify it's in the URL
    scope_in_url = f"scope={quote(SCOPES, safe='')}" in query_string
    logger.info(f"OAuth install: Scope parameter in URL: {scope_in_url}")
    if not scope_in_url:
        logger.error(
            f"❌ CRITICAL: Scope parameter missing from OAuth URL! Query string: {query_string[:200]}"
        )
    else:
        logger.info(f"✅ OAuth install: Scope parameter correctly included in URL")

    # Final validation before redirect
    if (
        not full_auth_url.startswith("https://")
        or ".myshopify.com" not in full_auth_url
    ):
        logger.error(f"❌ CRITICAL: Generated invalid OAuth URL!")
        logger.error(f"   - URL: {full_auth_url[:200]}...")
        logger.error(f"   - Shop: {shop}")
        logger.error(f"   - This will fail - aborting OAuth flow")
        return redirect(
            "/settings/shopify?error=Failed to generate valid OAuth URL. Please check your shop domain."
        )

    # CRITICAL: Also check if we're being accessed from admin.shopify.com (embedded context)
    # Even if host param is missing, if Referer is from admin.shopify.com, we're in an iframe
    is_embedded = bool(host)
    if not is_embedded:
        referer = request.headers.get("Referer", "")
        if referer and ("admin.shopify.com" in referer or "myshopify.com" in referer):
            # Likely embedded - try to extract host from referer or use a default
            # If we can't get host, we'll use window.top.location.href fallback
            is_embedded = True
            logger.info(f"Detected embedded context from Referer: {referer[:50]}...")

    # If embedded context detected, use JavaScript to breakout of iframe for OAuth
    if is_embedded:
        logger.info(f"➡️ Embedded OAuth install detected for {shop}, using App Bridge v3 breakout")
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://unpkg.com/@shopify/app-bridge@3"></script>
            <script>
                const authUrl = "{full_auth_url}";
                // [ABSOLUTE] window.top.location.href MUST be a full URL
                if (window.top !== window.self) {{
                    window.top.location.href = authUrl;
                }} else {{
                    window.location.href = authUrl;
                }}
            </script>
        </head>
        <body>
            <p>Redirecting to Shopify for authentication... <a href="{full_auth_url}">Click here if you are not redirected.</a></p>
        </body>
        </html>
        ''', 200

    # Non-embedded: regular redirect works fine
    logger.info(f"🚀 OAuth Install: Redirecting to Shopify for authorization")
    logger.info(f"   - Shop: {shop}")
    logger.info(f"   - URL: {full_auth_url[:100]}...")
    logger.info("=== OAUTH INSTALL DEBUG END ===")
    
    return redirect(full_auth_url)


@oauth_bp.route("/auth/callback")
@oauth_bp.route("/oauth/auth/callback")  # Legacy route for backwards compatibility
@oauth_bp.route("/callback")  # Alternative route for compatibility
def callback():
    """Handle Shopify OAuth callback"""
    import traceback

    # CRITICAL: Reject bot/crawler requests that aren't legitimate OAuth callbacks
    # Bots often hit callback URLs with Range headers or missing/empty OAuth parameters
    user_agent = request.headers.get("User-Agent", "")
    has_range_header = "Range" in request.headers

    # Check for VALID (non-empty) OAuth parameters
    code = request.args.get("code", "").strip()
    shop = request.args.get("shop", "").strip()
    has_valid_oauth_params = bool(code and shop and len(code) > 0 and len(shop) > 0)

    # If this looks like a bot request (has Range header or generic User-Agent) and missing/empty OAuth params
    if (
        has_range_header
        or "bot" in user_agent.lower()
        or "crawler" in user_agent.lower()
    ) and not has_valid_oauth_params:
        logger.info(f"🤖 Rejected bot/crawler request to OAuth callback")
        logger.info(f"   - User-Agent: {user_agent[:50]}")
        logger.info(f"   - Has Range header: {has_range_header}")
        logger.info(f"   - Code param: '{code}' (empty: {len(code) == 0})")
        logger.info(f"   - Shop param: '{shop}' (empty: {len(shop) == 0})")
        return "Not Found", 404

    # DEBUGGING: Log all callback details
    logger.info("=== OAUTH CALLBACK DEBUG START ===")
    logger.info(f"Callback URL: {request.url}")
    logger.info(f"Callback args: {dict(request.args)}")
    logger.info(f"Callback headers: {dict(request.headers)}")
    logger.info(f"Session before callback: {dict(session)}")

    # Check if this is a 404 scenario
    logger.info(f"Route matched: oauth.callback")
    logger.info(f"Blueprint registered: {oauth_bp.name}")

    # Log all received parameters for debugging
    logger.info(f"OAuth callback received parameters: {dict(request.args)}")

    try:
        result = _handle_oauth_callback()
        logger.info("=== OAUTH CALLBACK DEBUG SUCCESS ===")
        return result
    except Exception as e:
        logger.error("=== OAUTH CALLBACK DEBUG EXCEPTION ===")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception message: {str(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        error_trace = traceback.format_exc()
        logger.error(f"OAuth callback EXCEPTION: {str(e)}")
        logger.error(f"Full traceback:\n{error_trace}")
        return f"OAuth error: {str(e)}", 500


def _handle_oauth_callback():
    """Internal handler for OAuth callback - separated for better error handling"""
    # CRITICAL: Check API credentials before proceeding
    if not SHOPIFY_API_KEY or not SHOPIFY_API_SECRET:
        logger.error("OAuth callback failed: Missing API credentials")
        return "Configuration error: API credentials not set", 500

    # Log all parameters for debugging
    all_params = dict(request.args)
    logger.info(f"OAuth callback parameters: {all_params}")

    shop = request.args.get("shop")
    code = request.args.get("code")
    state = request.args.get("state")

    logger.info(f"📥 OAuth Callback: Received parameters")
    logger.info(f"   - Shop: {shop}")
    logger.info(f"   - Code: {'present (' + code[:10] + '...)' if code else 'MISSING'}")
    logger.info(f"   - State: {state}")
    logger.info(f"   - HMAC: {'present' if request.args.get('hmac') else 'MISSING'}")

    if not shop or not code:
        logger.error(f"❌ OAuth callback FAILED: Missing required parameters")
        return "Missing required parameters (shop or code)", 400

    # [SECURITY] Verify State Nonce
    expected_nonce = session.pop("shopify_nonce", None)
    
    if not state or "|" not in state:
        logger.error(f"❌ OAuth callback FAILED: Invalid or missing state parameter")
        return "Invalid state parameter", 400
        
    state_parts = state.split("||")[0].split("|")
    if len(state_parts) != 2:
        logger.error(f"❌ OAuth callback FAILED: Malformed state parameter structure")
        return "Malformed state parameter", 400
        
    state_shop, state_nonce = state_parts
    
    if state_nonce != expected_nonce:
        logger.error(f"❌ OAuth callback FAILED: State nonce mismatch (CSRF Protection)")
        logger.error(f"   - Expected: {expected_nonce}")
        logger.error(f"   - Received: {state_nonce}")
        return "Security verification failed: State mismatch", 403
        
    if state_shop != shop:
        logger.error(f"❌ OAuth callback FAILED: State shop mismatch")
        logger.error(f"   - Expected: {shop}")
        logger.error(f"   - Received: {state_shop}")
        return "Security verification failed: Shop mismatch", 403

    logger.info("✅ State nonce verification successful")

    # Verify HMAC
    logger.info("🔐 Verifying HMAC signature...")
    hmac_verified = verify_hmac(request.args)
    if not hmac_verified:
        logger.error("❌ OAuth callback FAILED: HMAC verification failed")
        logger.error(f"   - Shop: {shop}")
        logger.error(f"   - Received HMAC: {request.args.get('hmac', 'NONE')}")
        logger.error(
            f"   - This could indicate a security issue or misconfigured API secret"
        )
        return "HMAC verification failed", 403
    logger.info("✅ HMAC verification successful")

    # Exchange code for access token
    # CRITICAL: Log which API key is being used for OAuth (for debugging)
    current_api_key = os.getenv("SHOPIFY_API_KEY", "NOT_SET")
    if current_api_key and current_api_key != "NOT_SET" and len(current_api_key) >= 8:
        logger.info(
            f"OAUTH DEBUG: Using API key for token exchange: {current_api_key[:8]}... (length: {len(current_api_key)})"
        )
    else:
        logger.error(
            f"OAUTH DEBUG: API key is NOT SET or invalid! current_api_key={current_api_key}"
        )
    logger.info(f"OAUTH DEBUG: Shop: {shop}")

    # Normalize shop domain consistency
    original_shop = shop
    shop = (
        shop.lower()
        .replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .strip()
    )
    if not shop.endswith(".myshopify.com") and "." not in shop:
        shop = f"{shop}.myshopify.com"

    if original_shop != shop:
        logger.info(f"🔧 Normalized shop domain: '{original_shop}' → '{shop}'")

    logger.info(f"🔄 Exchanging authorization code for access token...")
    access_token = exchange_code_for_token(shop, code)

    if not access_token:
        logger.error(f"❌ OAuth callback FAILED: Failed to get access token")
        logger.error(f"   - Shop: {shop}")
        logger.error(f"   - Code was present: {bool(code)}")
        logger.error(f"   - Check if API credentials are correct")
        return "Failed to get access token", 500

    logger.info(f"✅ Access token received successfully (length: {len(access_token)})")

    logger.info(
        f"OAUTH DEBUG: Access token received: {access_token[:10]}... (first 10 chars)"
    )
    logger.info(f"OAUTH DEBUG: This token is tied to API key: {current_api_key[:8]}...")

    # Get shop information to extract shop_id
    logger.info(f"🏪 Fetching shop information...")
    shop_info = get_shop_info(shop, access_token)

    if shop_info:
        logger.info(f"✅ Shop info retrieved: {shop_info.get('name', 'Unknown')}")
    else:
        logger.warning("⚠️ Failed to retrieve shop info (non-critical)")

    # Use centralized utility for safe parsing
    from shopify_utils import parse_gid

    shop_gid = shop_info.get("id") if shop_info else None
    shop_id = parse_gid(shop_gid)

    if shop_gid and not shop_id:
        logger.warning(f"Failed to parse shop_id from GID: {shop_gid}")

    # Check if user is already logged in (e.g., manually connecting from settings page)
    user = None
    try:
        if current_user.is_authenticated:
            user_id = current_user.get_id()
            if user_id:
                user = User.query.get(int(user_id))
                if user:
                    logger.info(
                        f"👤 OAuth callback: Using existing logged-in user {user.email} (ID: {user.id})"
                    )
    except Exception as e:
        logger.debug(f"Could not get current_user: {e}")
        pass

    if not user:
        # For OAuth connections, create/find user based on shop domain
        shop_email = f"{shop}@shopify.com"
        logger.info(f"🔍 Looking for user with email: {shop_email}")
        try:
            user = User.query.filter_by(email=shop_email).first()
            if not user:
                logger.info(f"🆕 Creating new user for shop {shop}")
                from datetime import datetime, timedelta, timezone

                user = User(
                    email=shop_email,
                    password_hash="oauth_user",  # OAuth users don't need passwords
                    trial_started_at=datetime.now(timezone.utc),
                    trial_ends_at=datetime.now(timezone.utc) + timedelta(days=7),
                )
                db.session.add(user)
                db.session.commit()
                logger.info(
                    f"✅ Created new shop-based user {user.email} (ID: {user.id})"
                )
            else:
                logger.info(
                    f"✅ Found existing shop-based user {user.email} (ID: {user.id})"
                )
        except Exception as e:
            logger.error(f"❌ Error creating/finding user: {e}")
            logger.error(f"   - Shop: {shop}")
            logger.error(f"   - Email: {shop_email}")
            db.session.rollback()
            return "Failed to create user account", 500

    # CRITICAL: Log which API key was used to generate this access_token
    current_api_key = os.getenv("SHOPIFY_API_KEY", "NOT_SET")
    if current_api_key and current_api_key != "NOT_SET" and len(current_api_key) >= 8:
        api_key_preview = current_api_key[:8]
        logger.info(
            f"OAUTH COMPLETE: Generated new access_token using Partners API key: {api_key_preview}... (length: {len(current_api_key)})"
        )
        logger.info(
            f"OAUTH COMPLETE: This access_token is tied to Partners app: {api_key_preview}..."
        )
    else:
        logger.error(
            f"OAUTH COMPLETE: WARNING - API key is NOT SET or invalid! current_api_key={current_api_key}"
        )

    # Store Shopify credentials with proper error handling
    logger.info(f"💾 Storing Shopify credentials for shop {shop}...")
    store = ShopifyStore.query.filter_by(shop_url=shop, user_id=user.id).first()

    if store:
        # Update existing store
        logger.info(f"🔄 Updating existing store connection for {shop}")
        try:
            from data_encryption import encrypt_access_token

            encrypted_token = encrypt_access_token(access_token)
            if encrypted_token is None:
                logger.warning("⚠️ Encryption failed for token, storing as plaintext")
                encrypted_token = access_token

            store.access_token = encrypted_token
            store.shop_id = shop_id
            store.is_active = True
            store.is_installed = True
            store.uninstalled_at = None
            logger.info(f"✅ Updated existing store {shop} - set is_active=True")
        except Exception as e:
            logger.error(f"❌ Error updating store: {e}")
            logger.error(f"   - Shop: {shop}")
            logger.error(f"   - User ID: {user.id}")
            db.session.rollback()
            return "Failed to update store connection", 500
    else:
        # Create new store
        logger.info(f"🆕 Creating new store connection for {shop}")
        try:
            from data_encryption import encrypt_access_token

            encrypted_token = encrypt_access_token(access_token)
            if encrypted_token is None:
                logger.warning("⚠️ Encryption failed for token, storing as plaintext")
                encrypted_token = access_token

            store = ShopifyStore(
                user_id=user.id,
                shop_url=shop,
                shop_id=shop_id,
                access_token=encrypted_token,
                is_active=True,
                is_installed=True,
                uninstalled_at=None,
            )
            db.session.add(store)
            logger.info(f"✅ Created new store {shop} - set is_active=True")
        except Exception as e:
            logger.error(f"❌ Error creating store: {e}")
            logger.error(f"   - Shop: {shop}")
            logger.error(f"   - User ID: {user.id}")
            db.session.rollback()
            return "Failed to create store connection", 500

    try:
        db.session.commit()
        logger.info(f"✅ Successfully saved store connection to database")
        
        # [TITAN] Identity Weld: Inextricably link User to the new active Store
        try:
            user.current_store_id = store.id
            db.session.commit()
            logger.info(f"TITAN [WELD] User {user.id} welded to Store {store.id}")
            
            # Force these into the session so TITAN sees them immediately
            session['shop'] = shop
            session['active_store_id'] = store.id
            session.permanent = True
            session.modified = True
        except Exception as we:
            db.session.rollback()
            logger.error(f"TITAN [ERROR] Identity weld failed: {we}")

        # [LEGEND TIER] Invalidate Redis Cache for fresh settings
        try:
            store.invalidate_cache()
        except Exception as ce:
            logger.error(f"Cache invalidation failed: {ce}")
        
        # Automate Webhook Registration
        try:
            from shopify_integration import ShopifyClient
            client = ShopifyClient(shop, access_token)
            client.register_webhooks()
        except Exception as e:
            logger.error(f"Failed to register webhooks during OAuth for {shop}: {e}")
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Error saving store to database: {e}")
        logger.error(f"   - Shop: {shop}")
        logger.error(f"   - User ID: {user.id}")
        return "Failed to save store connection", 500

    # BULLETPROOF: Persist shop and host in session for subsequent requests
    session.permanent = True
    session.modified = True

    # Handle redirect after OAuth - check if this is an embedded app (App Store installation)
    # Shopify sends 'host' parameter for embedded apps
    # Extract host BEFORE using it for login logic
    host = request.args.get("host")

    # Also check state for host (in case it was passed through from install endpoint)
    state = request.args.get("state", "")
    if state and "||" in state and not host:
        # State contains shop||host format
        parts = state.split("||", 1)
        if len(parts) == 2:
            host = unquote(parts[1])

    # Store shop context in session with multiple keys for reliability
    session["shop"] = shop
    session["current_shop"] = shop  # Backup key
    session["shop_domain"] = shop.replace("https://", "").replace("http://", "")
    session["user_id"] = user.id
    session["_authenticated"] = True

    # Store host if available (for embedded apps)
    if host:
        session["host"] = host
        session["embedded"] = True
        session["is_embedded"] = True  # Additional flag

    # Force session save immediately
    try:
        session.permanent = True
        session.modified = True
        # Additional session data for debugging
        session["oauth_completed"] = True
        from datetime import datetime

        session["last_oauth"] = datetime.utcnow().isoformat()
    except Exception as session_error:
        logger.error(f"Session save error: {session_error}")

    logger.info(
        f"✅ Context prepared: shop={shop}, user_id={user.id}, host={bool(host) if host else False}"
    )

    # Compliance webhooks (GDPR) are handled manually in Partners Dashboard
    # register_compliance_webhooks(shop, access_token)

    # LEVEL 100: KILLED login_user(). Authentication is now per-request via JWT.
    # HARDENED RECOVERY: We still need a session for the initial redirect landing.
    # Since OAuth is fully verified (HMAC + Code), login_user is safe here.
    from flask_login import login_user
    login_user(user, remember=False)
    
    is_embedded = bool(host)

    # Store critical session data with error handling
    try:
        session.permanent = True
        session["shop"] = shop
        session["current_shop"] = shop
        session["shop_domain"] = shop.replace("https://", "").replace("http://", "")
        session["_user_id"] = user.id
        session["user_id"] = user.id # Legacy fallback
        session["_authenticated"] = True
        session["oauth_completed"] = True
        from datetime import datetime

        session["last_oauth"] = datetime.utcnow().isoformat()

        if host:
            session["host"] = host
            session["embedded"] = True
            session["is_embedded"] = True

        # Force session save
        session.modified = True

        logger.info(
            f"✅ OAuth complete: user {user.id}, shop {shop}, embedded: {bool(host)}"
        )

    except Exception as session_error:
        logger.error(f"Session management error: {session_error}")
        # Continue anyway - don't fail OAuth on session issues

    if is_embedded:
        logger.info(f"OAuth complete for embedded context")
    else:
        logger.info(f"OAuth complete for standalone context")

    # After OAuth completes, redirect to settings with success message
    logger.info("===== OAUTH FLOW COMPLETED SUCCESSFULLY =====")
    logger.info(f"   - Shop: {shop}")
    logger.info(f"   - User ID: {user.id}")
    logger.info(f"   - User Email: {user.email}")
    logger.info(f"   - Store ID: {store.id if store else 'N/A'}")
    logger.info(f"   - Embedded: {is_embedded}")
    logger.info(f"   - Session established: {session.get('oauth_completed', False)}")

    # CRITICAL: If host parameter is present, we MUST use App Bridge redirect
    # Shopify requires this for all embedded app requests
    logger.info(f"   - Host parameter present: {bool(host)}")

    # CRITICAL: Use the robust oauth_redirect.html template instead of hardcoded JS
    # This correctly handles shop and host parameters for App Bridge frame escape
    # [FINALITY] Small App Bridge JS redirect to ensure top-level breakout
    # Constructed following Shopify App Bridge v3 best practices
    try:
        decoded_host = base64.b64decode(host).decode('utf-8') if host else ""
    except Exception:
        decoded_host = ""
    
    clean_host = decoded_host.rstrip('/') if decoded_host else "admin.shopify.com"
    app_handle = os.getenv("SHOPIFY_APP_HANDLE", "employee-suite-7")
    full_url = f"https://{clean_host}/apps/{app_handle}/dashboard?shop={shop}&host={host}"

    return f'''
    <script src="https://unpkg.com/@shopify/app-bridge@3"></script>
    <script>
        const host = "{host}";
        const shop = "{shop}";
        const redirectUrl = "{full_url}";
        
        // Use App Bridge to escape the iframe securely
        if (window.top !== window.self) {{
            window.top.location.href = redirectUrl;
        }} else {{
            window.location.href = redirectUrl;
        }}
    </script>
    ''', 200


# TITAN: HMAC Verification Cache (Reduce Latency)
HMAC_CACHE = {}

def verify_hmac(params):
    """Verify Shopify HMAC with TITAN caching"""
    hmac_to_verify = params.get("hmac")
    shop = params.get("shop")
    
    if not hmac_to_verify:
        logger.error("HMAC verification failed: No hmac parameter in request")
        return False

    # 1. Check TITAN Cache
    cache_key = f"{shop}:{hmac_to_verify}"
    if cache_key in HMAC_CACHE:
        expiry = HMAC_CACHE[cache_key]
        if time.time() < expiry:
            return True
        else:
            del HMAC_CACHE[cache_key]

    # CRITICAL: Check that API secret is set
    if not SHOPIFY_API_SECRET:
        logger.error("HMAC verification failed: SHOPIFY_API_SECRET is not set!")
        return False

    # Create copy without hmac
    params_copy = dict(params)
    params_copy.pop("hmac", None)

    # Build query string
    query_string = "&".join([f"{k}={v}" for k, v in sorted(params_copy.items())])

    try:
        # Calculate HMAC
        calculated_hmac = hmac.new(
            SHOPIFY_API_SECRET.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        result = hmac.compare_digest(calculated_hmac, hmac_to_verify)
        
        # Cache successful verification for 5 minutes
        if result:
            HMAC_CACHE[cache_key] = time.time() + 300
            # Periodically clean cache if it gets too large
            if len(HMAC_CACHE) > 1000:
                HMAC_CACHE.clear()
                
        return result
    except Exception as e:
        logger.error(f"HMAC verification exception: {e}")
        return False


def exchange_code_for_token(shop, code):
    """Exchange authorization code for access token"""
    url = f"https://{shop}/admin/oauth/access_token"

    payload = {
        "client_id": SHOPIFY_API_KEY,
        "client_secret": SHOPIFY_API_SECRET,
        "code": code,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            try:
                data = response.json()
                access_token = (
                    data.get("access_token") if isinstance(data, dict) else None
                )
                granted_scopes = data.get("scope", "") if isinstance(data, dict) else ""
                if access_token:
                    logger.info(f"OAuth token exchange: Requested scopes: {SCOPES}")
                    logger.info(
                        f"OAuth token exchange: Granted scopes: {granted_scopes}"
                    )
                    # Check if scopes match (order doesn't matter)
                    requested_set = set([s.strip() for s in SCOPES.split(",")])
                    granted_set = (
                        set([s.strip() for s in granted_scopes.split(",")])
                        if granted_scopes
                        else set()
                    )
                    if requested_set != granted_set:
                        missing = requested_set - granted_set
                        extra = granted_set - requested_set
                        logger.error(
                            f"⚠️ SCOPE MISMATCH: Requested {SCOPES} but got {granted_scopes}"
                        )
                        if missing:
                            logger.error(f"⚠️ MISSING SCOPES: {missing}")
                            logger.error(
                                f"❌ CRITICAL: Missing scopes will cause 403 errors on API calls!"
                            )
                            logger.error(
                                f"❌ ACTION REQUIRED: Go to Shopify Partners Dashboard → Your App → API permissions"
                            )
                            logger.error(
                                f"❌ Ensure these scopes are CHECKED: {', '.join(missing)}"
                            )
                        if extra:
                            logger.warning(f"⚠️ EXTRA SCOPES: {extra}")
                    else:
                        logger.info(f"✅ Scopes match: {granted_scopes}")
                return access_token
            except (ValueError, KeyError) as e:
                logger.error(f"Error parsing access token response: {e}")
                return None
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting access token: {e}")
        return None


def get_shop_info(shop, access_token):
    """Get shop information including shop_id using GraphQL"""
    try:
        from shopify_graphql import ShopifyGraphQLClient

        client = ShopifyGraphQLClient(shop, access_token)

        query = """
        query {
            shop {
                id
                name
                email
                myshopifyDomain
                plan {
                    displayName
                    partnerDevelopment
                    shopifyPlus
                }
            }
        }
        """

        result = client.execute_query(query)
        if "error" in result:
            logger.error(f"Failed to get shop info via GraphQL: {result['error']}")
            return None

        return result.get("shop", {})

    except Exception as e:
        logger.error(f"Failed to get shop info: {e}")

    return None




def get_install_url(shop):
    """Generate installation URL for a shop"""
    return f"/oauth/install?shop={shop}"
