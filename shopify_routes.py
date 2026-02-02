from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template_string,
    request,
    url_for,
)
from flask_login import current_user, login_required

from config import SHOPIFY_API_VERSION

# Remove this line:
# from access_control import require_access
from input_validation import sanitize_input, validate_url
from logging_config import logger
from models import ShopifyStore, db
from session_token_verification import verify_session_token

shopify_bp = Blueprint("shopify", __name__)


def safe_redirect(url, shop=None, host=None):
    """
    Safe redirect that works in both embedded and standalone contexts.
    For embedded apps, uses App Bridge Redirect action (Shopify 2025+ compliant).
    For standalone, uses regular Flask redirect.
    """
    # Check if we're in an embedded context
    is_embedded = bool(host) or bool(shop) or request.args.get("embedded") == "1"

    if is_embedded:
        # Embedded app - use App Bridge Redirect (compliant with Shopify frame policies)
        redirect_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Redirecting...</title>
    <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
    <script>
        (function() {{
            var shopOrigin = '{shop or ""}';
            var hostParam = '{host or ""}';
            var targetUrl = '{url}';

            // Use App Bridge for Shopify URLs (OAuth, admin, etc.)
            if (targetUrl.includes('myshopify.com') || targetUrl.includes('shopify.com')) {{
                if (window.shopify && window.shopify.Redirect) {{
                    window.shopify.Redirect.dispatch(window.shopify.Redirect.Action.REMOTE, targetUrl);
                }} else {{
                    // Fallback: Shopify handles OAuth redirects at HTTP level
                    window.location.href = targetUrl;
                }}
            }} else {{
                // Internal app URLs - standard redirect
                window.location.href = targetUrl;
            }}
        }})();
    </script>
    <noscript>
        <meta http-equiv="refresh" content="0;url={url}">
    </noscript>
</head>
<body>
    <p>Redirecting... <a href="{url}">Click here if not redirected</a></p>
</body>
</html>"""
        return Response(redirect_html, mimetype="text/html")
    else:
        # Standalone - use regular Flask redirect
        return redirect(url)


SETTINGS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Settings - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f6f6f7;
            color: #202223;
            -webkit-font-smoothing: antialiased;
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
        .logo {
            font-size: 16px;
            font-weight: 600;
            color: #202223;
            text-decoration: none;
            letter-spacing: -0.2px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .nav-btn {
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            color: #6d7175;
            transition: background 0.15s;
        }
        .nav-btn:hover {
            background: #f6f6f7;
            color: #202223;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 32px 24px;
        }
        .page-title {
            font-size: 28px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 8px;
            letter-spacing: -0.3px;
        }
        .page-subtitle {
            font-size: 15px;
            color: #6d7175;
            margin-bottom: 32px;
        }
        .card {
            background: #ffffff;
            border: 1px solid #e1e3e5;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 20px;
        }
        .card-header {
            margin-bottom: 20px;
        }
        .card-title {
            font-size: 17px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 4px;
        }
        .card-subtitle {
            font-size: 14px;
            color: #6d7175;
        }
        .status-connected {
            display: inline-block;
            padding: 6px 12px;
            background: #e3fcef;
            color: #008060;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 16px;
        }
        .info-grid {
            display: grid;
            gap: 16px;
            margin: 20px 0;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 16px 0;
            border-bottom: 1px solid #e1e3e5;
            font-size: 14px;
        }
        .info-row:last-child {
            border-bottom: none;
        }
        .info-label {
            color: #6d7175;
            font-weight: 400;
        }
        .info-value {
            color: #202223;
            font-weight: 500;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-label {
            display: block;
            font-size: 13px;
            font-weight: 500;
            color: #202223;
            margin-bottom: 6px;
        }
        .form-input {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #e1e3e5;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
            background: #ffffff;
            transition: border-color 0.15s;
        }
        .form-input:focus {
            outline: none;
            border-color: #008060;
            box-shadow: 0 0 0 1px #008060;
        }
        .form-help {
            font-size: 13px;
            color: #6d7175;
            margin-top: 6px;
        }
        .btn {
            padding: 10px 16px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: background 0.15s;
        }
        .btn-primary {
            background: #008060;
            color: #fff;
        }
        .btn-primary:hover {
            background: #006e52;
        }
        .btn-danger {
            background: #d72c0d;
            color: #fff;
        }
        .btn-danger:hover {
            background: #bf280a;
        }
        .banner-success {
            background: #e3fcef;
            border: 1px solid #b2f5d1;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
            color: #008060;
            font-weight: 400;
        }
        .banner-error {
            background: #fff4f4;
            border: 1px solid #fecaca;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
            color: #d72c0d;
            font-weight: 400;
        }

        /* Mobile */
        @media (max-width: 768px) {
            .container { padding: 24px 16px; }
            .page-title { font-size: 24px; }
            .card { padding: 20px; }
            .header-content { padding: 0 16px; height: 56px; }
            .info-row { flex-direction: column; gap: 4px; }
        }
        @media (max-width: 480px) {
            .container { padding: 20px 12px; }
            .page-title { font-size: 20px; }
            .card { padding: 16px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <a href="/dashboard" style="text-decoration: none; color: inherit; display: flex; align-items: center; gap: 10px; font-weight: 600;" class="logo">
                <span>Employee Suite</span>
            </a>
            <a href="/dashboard" class="nav-btn">Back to Dashboard</a>
        </div>
    </div>

    <div class="container">
        <h1 class="page-title">Settings</h1>
        <p class="page-subtitle">Manage your Shopify connection and account</p>

        {% if success %}
        <div class="banner-success" style="animation: fadeIn 0.5s ease-in;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 24px;">🎉</span>
                <div>
                    <strong style="display: block; margin-bottom: 4px;">{{ success }}</strong>
                    <span style="font-size: 14px; opacity: 0.9;">You're all set! Head back to the dashboard to start monitoring your store.</span>
                </div>
            </div>
        </div>
        {% endif %}

        {% if error %}
        <div class="banner-error">{{ error }}</div>
        {% endif %}

        {% if is_subscribed %}
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Subscription</h2>
                <p class="card-subtitle">Manage your subscription</p>
            </div>
            <div class="info-grid">
                <div class="info-row">
                    <span class="info-label">Status</span>
                    <span class="info-value">Active</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Plan</span>
                    <span class="info-value">Employee Suite Pro</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Billing</span>
                    <span class="info-value">$99/month</span>
                </div>
            </div>
            <form method="POST" action="{{ url_for('shopify.cancel_subscription') }}" style="margin-top: 20px;">
                {% if shop %}<input type="hidden" name="shop" value="{{ shop }}">{% endif %}
                {% if host %}<input type="hidden" name="host" value="{{ host }}">{% endif %}
                <button type="submit" class="btn btn-danger" onclick="return confirm('Cancel subscription? You will lose access to all features.')">Cancel Subscription</button>
            </form>
        </div>
        {% endif %}

        {% if store %}
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Shopify Connection</h2>
                <span class="status-connected">✓ Connected</span>
            </div>
            <div class="info-grid">
                <div class="info-row">
                    <span class="info-label">Store URL</span>
                    <span class="info-value">{{ store.shop_url }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Connected</span>
                    <span class="info-value">{{ store.created_at.strftime('%B %d, %Y') }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Shopify Admin</span>
                    <span class="info-value">
                        <a href="https://admin.shopify.com/store/{{ store.shop_url.replace('.myshopify.com', '') }}" target="_blank" rel="noopener noreferrer" style="color: #008060; text-decoration: none; font-weight: 500;">Open in new tab →</a>
                    </span>
                </div>
            </div>
            <form method="POST" action="{{ url_for('shopify.disconnect_store') }}" style="margin-top: 20px;">
                {% if shop %}<input type="hidden" name="shop" value="{{ shop }}">{% endif %}
                {% if host %}<input type="hidden" name="host" value="{{ host }}">{% endif %}
                <button type="submit" class="btn btn-danger" onclick="return confirm('Disconnect store?')">Disconnect Store</button>
            </form>
        </div>
        {% else %}
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Connect Shopify Store</h2>
                <p class="card-subtitle">Connect your store to start monitoring your operations</p>
            </div>

            <!-- OAuth Quick Connect (1-2 clicks) -->
            <div style="margin-bottom: 24px; padding: 24px; background: #fafafa; border: 1px solid #e5e5e5; border-radius: 16px;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                    <span style="font-size: 24px;">✨</span>
                    <h3 style="font-size: 18px; font-weight: 600; color: #171717; margin: 0;">Quick Connect (Recommended)</h3>
                </div>
                <p style="font-size: 14px; color: #525252; margin-bottom: 20px; line-height: 1.6;">Connect your store in seconds with one click. No need to copy tokens manually. We'll redirect you to Shopify to authorize the connection.</p>
                <div>
                    <label for="shop_oauth" style="display: block; font-size: 14px; font-weight: 500; color: #171717; margin-bottom: 8px;">Enter your store domain</label>
                    <form method="GET" action="/install" style="display: flex; gap: 12px; align-items: flex-start; flex-wrap: wrap;">
                        <div style="flex: 1; min-width: 250px;">
                            <input type="text" id="shop_oauth" name="shop" class="form-input" placeholder="yourstore.myshopify.com" required style="width: 100%; font-size: 15px; padding: 12px;">
                            <p style="font-size: 12px; color: #737373; margin-top: 6px;">Enter your store domain (e.g., mystore.myshopify.com)</p>
                            {% if request.args.get('host') %}
                            <input type="hidden" name="host" value="{{ request.args.get('host') }}">
                            {% endif %}
                        </div>
                        <div style="display: flex; align-items: flex-start;">
                            <button type="submit" class="btn btn-primary" style="white-space: nowrap; padding: 12px 24px; font-size: 15px; font-weight: 600; background: #0ea5e9; border: none; height: 44px;">Connect with Shopify</button>
                        </div>
                    </form>
                </div>
                <div style="margin-top: 16px; padding: 12px; background: rgba(255,255,255,0.7); border-radius: 8px;">
                    <p style="font-size: 13px; color: #166534; margin: 0; display: flex; align-items: center; gap: 8px;">
                        <span>✓</span>
                        <span>Secure OAuth connection. You'll be redirected to Shopify to approve access.</span>
                    </p>
                </div>
            </div>

            <!-- Manual Connection (Advanced/Fallback) -->
            <details style="margin-top: 24px;">
                <summary style="font-size: 14px; font-weight: 500; color: #525252; cursor: pointer; padding: 14px; background: #fafafa; border-radius: 8px; border: 1px solid #e5e5e5; user-select: none;">
                    🔧 Advanced: Connect with Access Token (Manual Method)
                </summary>
                <div style="margin-top: 20px; padding: 20px; background: #fafafa; border-radius: 8px; border: 1px solid #e5e5e5;">
                    <p style="font-size: 13px; color: #737373; margin-bottom: 20px; line-height: 1.6;">
                        <strong>When to use this:</strong> Only if you need to connect a development store, custom app, or if the Quick Connect above doesn't work for your setup.
                    </p>
                    <form method="POST" action="{{ url_for('shopify.connect_store') }}">
                        {% if shop %}<input type="hidden" name="shop" value="{{ shop }}">{% endif %}
                        {% if host %}<input type="hidden" name="host" value="{{ host }}">{% endif %}
                        <div class="form-group">
                            <label class="form-label">Store URL</label>
                            <input type="text" name="shop_url" placeholder="yourstore.myshopify.com" class="form-input" required>
                            <p class="form-help">Your Shopify store URL</p>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Admin API Access Token</label>
                            <input type="password" name="access_token" class="form-input" placeholder="shpat_xxxxxxxxxxxx" required>
                            <p class="form-help">Get this from: <strong>Shopify Admin → Settings → Apps and sales channels → Develop apps → Create app → Admin API access token</strong><br>
                            <a href="https://admin.shopify.com" target="_blank" rel="noopener noreferrer" style="color: #008060; text-decoration: none; font-size: 13px; margin-top: 4px; display: inline-block;">Open Shopify Admin in new tab →</a></p>
                        </div>
                        <button type="submit" class="btn btn-primary" style="background: #0ea5e9;">Connect Store</button>
                    </form>
                </div>
            </details>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""


@shopify_bp.route("/settings/shopify")
def shopify_settings():
    """Shopify settings page - works in both embedded and standalone modes"""

    shop = request.args.get("shop", "")
    if shop:
        shop = (
            shop.lower()
            .replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
            .strip()
        )
        if not shop.endswith(".myshopify.com") and "." not in shop:
            shop = f"{shop}.myshopify.com"

    host = request.args.get("host", "")

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

    # If no user found, redirect to install (for embedded) or show message
    if not user:
        if shop and host:
            # Embedded mode - redirect to install using client-side redirect
            from flask import url_for

            install_url = url_for("oauth.install", shop=shop, host=host)
            # Use App Bridge compliant redirect
            redirect_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Install Required</title>
    <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
    <script>
        // App Bridge compliant redirect for embedded apps
        if (window.shopify && window.shopify.Redirect) {{
            window.shopify.Redirect.dispatch(window.shopify.Redirect.Action.APP, '{install_url}');
        }} else {{
            window.location.href = '{install_url}';
        }}
    </script>
</head>
<body>
    <p>Redirecting to install...</p>
    <a href="{install_url}">Click here if redirect doesn't work</a>
</body>
</html>"""
            return redirect_html
        else:
            # Standalone mode - redirect to login
            from flask import redirect, url_for

            return redirect(url_for("auth.login"))

    # Get user's store
    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()

    # Pass shop and host to template for links, and user subscription status
    return render_template_string(
        SETTINGS_HTML,
        store=store,
        success=request.args.get("success"),
        error=request.args.get("error"),
        shop=shop,
        host=host,
        is_subscribed=user.is_subscribed if user else False,
    )


@shopify_bp.route("/settings/shopify/connect", methods=["POST"])
def connect_store():
    """Connect store via manual token - works in both embedded and standalone modes"""
    shop_url = request.form.get("shop_url", "").strip()
    access_token = request.form.get("access_token", "").strip()
    shop = request.form.get("shop") or request.args.get("shop", "")
    if shop:
        shop = (
            shop.lower()
            .replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
            .strip()
        )
        if not shop.endswith(".myshopify.com") and "." not in shop:
            shop = f"{shop}.myshopify.com"

    host = request.form.get("host") or request.args.get("host", "")

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
        settings_url = url_for(
            "shopify.shopify_settings",
            error="Authentication required",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    # Input validation
    if not shop_url or not access_token:
        settings_url = url_for(
            "shopify.shopify_settings",
            error="Store URL and access token are required.",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    # Sanitize and validate shop URL
    shop_url = (
        sanitize_input(shop_url)
        .lower()
        .replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .strip()
    )
    if not shop_url.endswith(".myshopify.com") and "." not in shop_url:
        shop_url = f"{shop_url}.myshopify.com"

    # Validate Shopify URL format
    if not validate_url(shop_url):
        settings_url = url_for(
            "shopify.shopify_settings",
            error="Invalid Shopify store URL format. Use: yourstore.myshopify.com",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    # Validate access token (basic check - should be non-empty)
    if len(access_token) < 10:
        settings_url = url_for(
            "shopify.shopify_settings",
            error="Invalid access token format.",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    # WARNING: Manual access tokens from old apps won't work with new Partners API key
    # Recommend OAuth instead
    logger.warning(
        f"Manual access token connection attempted for {shop_url} by user {user.id}"
    )
    logger.warning(
        f"NOTE: Manual tokens from old apps may not work with new Partners API key. OAuth is recommended."
    )

    if ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first():
        settings_url = url_for(
            "shopify.shopify_settings",
            error="You already have a connected store. Disconnect it first.",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    # Validate the access_token works with current API key by testing a simple API call
    # Validate the access_token works with current API key by testing a simple API call
    try:
        from shopify_graphql import ShopifyGraphQLClient

        # Use GraphQL to validate token (modern approach)
        graphql_client = ShopifyGraphQLClient(shop_url, access_token)
        query = """
        query {
            shop {
                name
                id
                myshopifyDomain
            }
        }
        """
        result = graphql_client.execute_query(query)

        if "error" in result:
            # Invalid token - might be from old app
            logger.warning(
                f"Access token test failed for {shop_url}: {result['error']}"
            )
            settings_url = url_for(
                "shopify.shopify_settings",
                error=f'Access token validation failed: {result["error"]}. Please use the "Quick Connect" OAuth method instead.',
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)

    except Exception as e:
        logger.error(f"Error validating access token: {e}", exc_info=True)
        # Continue anyway - validation is optional
        pass
    except Exception as e:
        logger.error(f"Error validating access token: {e}", exc_info=True)
        # Continue anyway - validation is optional
        pass

    # Encrypt the token before storing (CRITICAL: same as OAuth flow)
    from data_encryption import encrypt_access_token

    encrypted_token = encrypt_access_token(access_token)

    # If encryption failed (returned None), store plaintext with warning (for backwards compatibility)
    if encrypted_token is None:
        logger.warning(
            f"Encryption failed for manual token, storing as plaintext (ENCRYPTION_KEY may not be set)"
        )
        encrypted_token = access_token

    new_store = ShopifyStore(
        user_id=user.id, shop_url=shop_url, access_token=encrypted_token, is_active=True
    )

    db.session.add(new_store)
    db.session.commit()

    logger.info(
        f"Manual access token connection successful for {shop_url} by user {user.id}"
    )
    settings_url = url_for(
        "shopify.shopify_settings",
        success="Store connected successfully!",
        shop=shop,
        host=host,
    )
    return safe_redirect(settings_url, shop=shop, host=host)


@shopify_bp.route("/settings/shopify/disconnect", methods=["POST"])
def disconnect_store():
    """Disconnect store - works in both embedded and standalone modes"""
    shop = request.form.get("shop") or request.args.get("shop", "")
    if shop:
        shop = (
            shop.lower()
            .replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
            .strip()
        )
        if not shop.endswith(".myshopify.com") and "." not in shop:
            shop = f"{shop}.myshopify.com"

    host = request.form.get("host") or request.args.get("host", "")

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
        settings_url = url_for(
            "shopify.shopify_settings",
            error="Authentication required",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    if store:
        try:
            # Use model method for consistent state management
            store.disconnect()
            db.session.commit()
            logger.info(
                f"Store {store.shop_url} disconnected and access_token cleared for user {user.id}"
            )
            settings_url = url_for(
                "shopify.shopify_settings",
                success="Store disconnected successfully! You can now reconnect with the new Partners app.",
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)
        except Exception as e:
            logger.error(f"Error disconnecting store: {e}", exc_info=True)
            try:
                db.session.rollback()
            except Exception:
                pass
            settings_url = url_for(
                "shopify.shopify_settings",
                error="Error disconnecting store. Please try again.",
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)
    settings_url = url_for(
        "shopify.shopify_settings", error="No active store found.", shop=shop, host=host
    )
    return safe_redirect(settings_url, shop=shop, host=host)


@shopify_bp.route("/settings/shopify/cancel", methods=["POST"])
def cancel_subscription():
    """Cancel user's Shopify subscription - works in both embedded and standalone modes"""
    import os

    import requests

    shop = request.form.get("shop") or request.args.get("shop", "")
    if shop:
        shop = (
            shop.lower()
            .replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
            .strip()
        )
        if not shop.endswith(".myshopify.com") and "." not in shop:
            shop = f"{shop}.myshopify.com"

    host = request.form.get("host") or request.args.get("host", "")

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
        settings_url = url_for(
            "shopify.shopify_settings",
            error="Authentication required",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    if not user.is_subscribed:
        settings_url = url_for(
            "shopify.shopify_settings",
            error="No active subscription found.",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    # Get user's Shopify store
    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    if not store:
        settings_url = url_for(
            "shopify.shopify_settings",
            error="No Shopify store connected.",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    if not store.charge_id:
        # No charge_id but marked as subscribed - just update the flag
        user.is_subscribed = False
        db.session.commit()
        settings_url = url_for(
            "shopify.shopify_settings",
            success="Subscription status updated.",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    try:
        # Use the centralized billing logic (GraphQL)
        from billing import cancel_app_subscription

        result = cancel_app_subscription(
            store.shop_url, store.get_access_token() or "", store.charge_id
        )

        if result.get("success"):
            user.is_subscribed = False
            store.charge_id = None
            db.session.commit()

            logger.info(f"Subscription cancelled for {store.shop_url}")

            # Send cancellation email
            try:
                from email_service import send_cancellation_email

                send_cancellation_email(user.email)
            except Exception as e:
                logger.error(f"Failed to send cancellation email: {e}")

            settings_url = url_for(
                "shopify.shopify_settings",
                success="Subscription cancelled successfully. You will retain access until the end of your billing period.",
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)
        else:
            logger.error(
                f"Failed to cancel Shopify subscription: {response.status_code} - {response.text}"
            )
            settings_url = url_for(
                "shopify.shopify_settings",
                error="Failed to cancel subscription. Please try again or contact support.",
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error during cancellation: {e}")
        settings_url = url_for(
            "shopify.shopify_settings",
            error=f"Network error: {str(e)}",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)
    except Exception as e:
        logger.error(f"Unexpected error during cancellation: {e}")
        settings_url = url_for(
            "shopify.shopify_settings",
            error="An unexpected error occurred. Please contact support.",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)
