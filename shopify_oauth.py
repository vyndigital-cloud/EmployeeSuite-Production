import hashlib
import hmac
import os
from urllib.parse import quote, unquote

import requests
from flask import Blueprint, redirect, request, session
from flask_login import current_user, login_user

from config import SHOPIFY_API_VERSION
from logging_config import logger
from models import ShopifyStore, User, db

oauth_bp = Blueprint("oauth", __name__)

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
        "https://employeesuite-production.onrender.com/auth/callback",
    )
    .strip()
    .strip('"')
    .strip("'")
)
# Access mode: offline = persistent token, online = session-based token
# Use offline for background operations (webhooks, cron jobs)
ACCESS_MODE = "offline"


@oauth_bp.route("/install")
def install():
    """Initiate Shopify OAuth - Professional error handling"""
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

    # Normalize shop domain - professional consistent normalization
    shop = (
        shop.lower()
        .replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .strip()
    )
    if not shop.endswith(".myshopify.com") and "." not in shop:
        shop = f"{shop}.myshopify.com"

    logger.info(f"Normalized install shop: {shop}")

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

    state_data = shop
    if host:
        # Encode host in state for embedded app installations
        # Use a separator that won't conflict with shop domain
        state_data = f"{shop}||{quote(host, safe='')}"

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
    logger.debug(f"OAuth install: Generated auth URL for shop {shop}")
    # Log scope parameter to verify it's in the URL
    scope_in_url = f"scope={quote(SCOPES, safe='')}" in query_string
    logger.info(f"OAuth install: Scope parameter in URL: {scope_in_url}")
    if not scope_in_url:
        logger.error(
            f"❌ CRITICAL: Scope parameter missing from OAuth URL! Query string: {query_string[:200]}"
        )
    else:
        logger.info(f"✅ OAuth install: Scope parameter correctly included in URL")

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

    # SIMPLEST SOLUTION: If embedded, show a link that opens in new window
    # No JavaScript, no redirects, no App Bridge complexity - just a simple link
    # This avoids ALL iframe loading issues
    if is_embedded:
        # If we have host, use it. Otherwise, try to extract from Referer or use fallback
        if not host:
            # Try one more time to extract from Referer URL params
            referer = request.headers.get("Referer", "")
            if referer:
                from urllib.parse import parse_qs, urlparse

                try:
                    parsed = urlparse(referer)
                    query_params = parse_qs(parsed.query)
                    if "host" in query_params:
                        host = query_params["host"][0]
                        logger.info(f"Extracted host from Referer: {host[:20]}...")
                except Exception:
                    pass

        logger.info(
            f"Embedded OAuth install detected for {shop}, showing link to open OAuth in new window"
        )

        # SIMPLEST FIX: Just show a link that opens in a new window
        # No JavaScript redirects, no App Bridge complexity - just works
        # Restore manual button - automatic redirects are often blocked in iframes
        from flask import render_template_string

        return render_template_string(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Connect Shopify - Employee Suite</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #f6f6f7; }}
                .card {{ background: white; padding: 32px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }}
                h1 {{ font-size: 20px; margin-bottom: 12px; color: #202223; }}
                p {{ font-size: 14px; color: #6d7175; margin-bottom: 24px; line-height: 1.5; }}
                .btn {{ background: #008060; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 500; display: inline-block; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Connect Your Store</h1>
                <p>Click the button below to authorize Employee Suite to manage your orders and inventory.</p>
                <a href="{full_auth_url}" target="_top" class="btn">Connect Your Shopify Store →</a>
                <div style="margin-top: 16px; font-size: 12px; color: #8c9196;">This will open the Shopify authorization screen.</div>
            </div>
        </body>
        </html>
        """)

    # Non-embedded: regular redirect works fine
    return redirect(full_auth_url)


@oauth_bp.route("/auth/callback")
def callback():
    """Handle Shopify OAuth callback"""
    import traceback

    # Log all received parameters for debugging
    logger.info(f"OAuth callback received parameters: {dict(request.args)}")

    try:
        return _handle_oauth_callback()
    except Exception as e:
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

    if not shop or not code:
        logger.error(f"OAuth callback failed: Missing parameters")
        logger.error(f"  shop: {shop}")
        logger.error(f"  code: {'present' if code else 'missing'}")
        logger.error(f"  state: {state}")
        logger.error(f"  all params: {all_params}")
        return "Missing required parameters (shop or code)", 400

    # Verify HMAC
    hmac_verified = verify_hmac(request.args)
    if not hmac_verified:
        logger.error("OAuth callback failed: HMAC verification failed")
        return "HMAC verification failed", 403

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
    shop = (
        shop.lower()
        .replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .strip()
    )
    if not shop.endswith(".myshopify.com") and "." not in shop:
        shop = f"{shop}.myshopify.com"

    access_token = exchange_code_for_token(shop, code)

    if not access_token:
        return "Failed to get access token", 500

    logger.info(
        f"OAUTH DEBUG: Access token received: {access_token[:10]}... (first 10 chars)"
    )
    logger.info(f"OAUTH DEBUG: This token is tied to API key: {current_api_key[:8]}...")

    # Get shop information to extract shop_id
    shop_info = get_shop_info(shop, access_token)

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
                    logger.info(f"OAuth callback: Using existing logged-in user {user.email} (ID: {user.id})")
    except Exception as e:
        logger.debug(f"Could not get current_user: {e}")
        pass

    if not user:
        # For OAuth connections, create/find user based on shop domain
        shop_email = f"{shop}@shopify.com"
        try:
            user = User.query.filter_by(email=shop_email).first()
            if not user:
                from datetime import datetime, timedelta, timezone
                user = User(
                    email=shop_email,
                    password_hash="oauth_user",  # OAuth users don't need passwords
                    trial_started_at=datetime.now(timezone.utc),
                    trial_ends_at=datetime.now(timezone.utc) + timedelta(days=7),
                )
                db.session.add(user)
                db.session.commit()
                logger.info(f"OAuth callback: Created new shop-based user {user.email} (ID: {user.id})")
            else:
                logger.info(f"OAuth callback: Found existing shop-based user {user.email} (ID: {user.id})")
        except Exception as e:
            logger.error(f"Error creating/finding user: {e}")
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
    store = ShopifyStore.query.filter_by(shop_url=shop, user_id=user.id).first()

    if store:
        # Update existing store
        try:
            from data_encryption import encrypt_access_token
            encrypted_token = encrypt_access_token(access_token)
            if encrypted_token is None:
                logger.warning("Encryption failed for token, storing as plaintext")
                encrypted_token = access_token

            store.access_token = encrypted_token
            store.shop_id = shop_id
            store.is_active = True
            store.is_installed = True
            store.uninstalled_at = None
            logger.info(f"Updated existing store {shop} - set is_active=True")
        except Exception as e:
            logger.error(f"Error updating store: {e}")
            return "Failed to update store connection", 500
    else:
        # Create new store
        try:
            from data_encryption import encrypt_access_token
            encrypted_token = encrypt_access_token(access_token)
            if encrypted_token is None:
                logger.warning("Encryption failed for token, storing as plaintext")
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
            logger.info(f"Created new store {shop} - set is_active=True")
        except Exception as e:
            logger.error(f"Error creating store: {e}")
            return "Failed to create store connection", 500

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving store to database: {e}")
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
        f"✅ Session bulletproofed: shop={shop}, user_id={user.id}, host={bool(host) if host else False}"
    )
    logger.info(f"✅ Session keys stored: {list(session.keys())}")

    # Register mandatory compliance webhooks (Shopify requirement)
    register_compliance_webhooks(shop, access_token)

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

    # Always log user in after successful OAuth
    is_embedded = bool(host)
    login_user(user, remember=not is_embedded)

    # Store critical session data
    session.permanent = True
    session["shop"] = shop
    session["current_shop"] = shop
    session["shop_domain"] = shop.replace("https://", "").replace("http://", "")
    session["user_id"] = user.id
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

    logger.info(f"✅ OAuth complete: user {user.id}, shop {shop}, embedded: {bool(host)}")

    logger.info(
        f"Session refreshed for user {user.id} (email: {user.email}) after OAuth callback - embedded: {is_embedded}"
    )

    if is_embedded:
        logger.info(f"OAuth login for embedded app (session token auth)")
    else:
        logger.info(f"OAuth login for standalone access (cookie auth)")

    # After OAuth completes, redirect appropriately
    if host:
        # For embedded apps, redirect to the app within Shopify admin
        admin_url = f"https://{shop}/admin/apps/{SHOPIFY_API_KEY}"
        logger.info(f"OAuth complete (embedded), redirecting to: {admin_url}")
        return redirect(admin_url)
    else:
        # For standalone, redirect to dashboard with shop parameter
        try:
            from flask import url_for
            dashboard_url = url_for("core.home", shop=shop)
        except Exception:
            dashboard_url = f"/dashboard?shop={shop}"
        logger.info(f"OAuth complete (standalone), redirecting to: {dashboard_url}")
        return redirect(dashboard_url)


def verify_hmac(params):
    """Verify Shopify HMAC"""
    hmac_to_verify = params.get("hmac")
    if not hmac_to_verify:
        logger.error("HMAC verification failed: No hmac parameter in request")
        return False

    # CRITICAL: Check that API secret is set before trying to use it
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

        return hmac.compare_digest(calculated_hmac, hmac_to_verify)
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


def register_compliance_webhooks(shop, access_token):
    """
    Register mandatory compliance webhooks via Admin API
    This ensures webhooks are registered even if shopify.app.toml isn't deployed via CLI
    """
    app_url = os.getenv(
        "SHOPIFY_APP_URL", "https://employeesuite-production.onrender.com"
    )
    api_version = SHOPIFY_API_VERSION

    # Mandatory compliance webhooks
    webhooks = [
        {
            "topic": "customers/data_request",
            "address": f"{app_url}/webhooks/customers/data_request",
            "format": "json",
        },
        {
            "topic": "customers/redact",
            "address": f"{app_url}/webhooks/customers/redact",
            "format": "json",
        },
        {
            "topic": "shop/redact",
            "address": f"{app_url}/webhooks/shop/redact",
            "format": "json",
        },
    ]

    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }

    for webhook in webhooks:
        url = f"https://{shop}/admin/api/{api_version}/webhooks.json"
        payload = {"webhook": webhook}

        try:
            # Check if webhook already exists
            list_url = f"https://{shop}/admin/api/{api_version}/webhooks.json?topic={webhook['topic']}"
            list_response = requests.get(list_url, headers=headers, timeout=10)

            if list_response.status_code == 200:
                existing = list_response.json().get("webhooks", [])
                # Check if webhook with this address already exists
                exists = any(w.get("address") == webhook["address"] for w in existing)
                if exists:
                    continue  # Already registered, skip

            # Create webhook
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                logger.info(
                    f"Successfully registered compliance webhook: {webhook['topic']} for shop {shop}"
                )
            elif response.status_code == 404:
                # GDPR compliance webhooks must be registered in Partners Dashboard, not via Admin API
                # This is expected for Partner apps - webhooks are already configured in app manifest
                logger.warning(
                    f"Webhook registration failed for {webhook['topic']}: "
                    f"{response.status_code} - {response.text[:200]}"
                )
            else:
                logger.warning(
                    f"Failed to register webhook {webhook['topic']}: {response.status_code} - {response.text}"
                )
        except Exception as e:
            logger.error(
                f"Error registering webhook {webhook['topic']}: {e}", exc_info=True
            )
