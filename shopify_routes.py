from datetime import datetime, timezone

from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user

from config import SHOPIFY_API_VERSION

# Remove this line:
# from access_control import require_access
from input_validation import sanitize_input, validate_url
from logging_config import logger
from models import ShopifyStore, db
from session_token_verification import verify_session_token
from shopify_utils import normalize_shop_url

shopify_bp = Blueprint("shopify", __name__)


from flask import render_template

from utils import safe_redirect


@shopify_bp.route("/connections", methods=["GET", "POST"])
@shopify_bp.route("/shopify/connections", methods=["GET", "POST"])
def connections_alias():
    """Alias for shopify_settings to fix 404s from frontend"""
    return shopify_settings()


@shopify_bp.route("/settings/shopify")
def shopify_settings():
    """Shopify settings page - works in both embedded and standalone modes"""

    from session_debug import check_cookie_compatibility, log_session_state
    from shopify_utils import normalize_shop_url

    # DEBUG: Log session state to diagnose iframe session amnesia
    log_session_state("shopify_settings - START")
    cookie_compat = check_cookie_compatibility()

    if cookie_compat.get("cookies_likely_blocked"):
        logger.error(
            "🚨 CRITICAL: Cookies likely blocked in this context! "
            f"HTTPS: {cookie_compat.get('is_https')}, "
            f"Embedded: {cookie_compat.get('is_embedded')}"
        )
        if cookie_compat.get("is_embedded"):
            from app_bridge_breakout import iframe_safe_redirect

            shop_param = request.args.get("shop")
            return iframe_safe_redirect(url_for("auth.login"), shop=shop_param)

    # Normalize shop URL
    shop = request.args.get("shop") or session.get("shop_domain")
    if shop:
        shop = normalize_shop_url(shop)
    
    # Ensure shop has a default if absolutely missing (needed for App Bridge init)
    if not shop:
        shop = "employee-suite.myshopify.com"

    host = request.args.get("host") or session.get("host")

    # ============================================================================
    # CRITICAL FIX: Check Flask-Login session FIRST before ANY other logic
    # ============================================================================
    user = None

    # PRIORITY 1: Check current_user.is_authenticated BEFORE anything else
    if current_user.is_authenticated:
        user = current_user
        logger.info(
            f"✅ shopify_settings: User {user.id} authenticated via Flask-Login - "
            f"Session _user_id={session.get('_user_id')}, "
            f"permanent={session.permanent}"
        )

        # STOP HERE - We have a valid authenticated user
        # Don't check shop parameters, don't do any other lookups
        # Just proceed to render the settings page

    # PRIORITY 2: Only if Flask-Login failed, try shop lookup (for embedded apps)
    elif shop:
        try:
            # Try to find user from shop (for embedded apps)
            store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
            if store and store.user:
                user = store.user
                # CRITICAL FIX: Actually log the user in!
                login_user(user)
                logger.info(
                    f"✅ Found user via shop lookup: {user.id} for shop {shop} - Logged in successfully"
                )
            else:
                logger.warning(f"❌ No ACTIVE store found for shop: {shop}")
        except Exception as e:
            logger.error(f"Error finding user in shopify_settings: {e}", exc_info=True)
            user = None
    else:
        logger.warning(f"❌ No authenticated user and no shop parameter")

    # Handle different authentication scenarios
    if not user:
        logger.warning(f"⚠️ shopify_settings: NO USER FOUND - Redirecting to install")
        from shopify_oauth import get_install_url
        install_url = get_install_url(shop)
        if host:
            install_url += f"&host={host}"
        return redirect(install_url)

        # CRITICAL FIX: This should NEVER happen if current_user.is_authenticated was True
        # Log this as a critical error for debugging
        if current_user.is_authenticated:
            logger.error(
                f"🚨 CRITICAL BUG: current_user.is_authenticated=True but user object is None! "
                f"Session data: _user_id={session.get('_user_id')}, "
                f"permanent={session.permanent}, "
                f"keys={list(session.keys())}"
            )
            # Force use current_user as fallback
            user = current_user
        else:
            # User is NOT authenticated via Flask-Login either
            # Import the App Bridge breakout utility
            from app_bridge_breakout import iframe_safe_redirect

            if shop:
                # Embedded app with shop but no user - start OAuth
                install_url = f"/oauth/install?shop={shop}"
                if host:
                    install_url += f"&host={host}"

                logger.info(
                    f"No user found for shop {shop}, redirecting to OAuth: {install_url}"
                )
                return iframe_safe_redirect(install_url, shop=shop)
            else:
                # No user, no shop, not authenticated - redirect to login
                logger.info(f"No authentication found, redirecting to login")
                return iframe_safe_redirect(url_for("auth.login"), shop=None)

    # User is authenticated - allow access even without shop (disconnected state)
    logger.info(f"✅ User {user.id} authenticated - allowing access to settings")

    # Get user's store
    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()

    # Pass shop and host to template for links, and user subscription status
    return render_template(
        "settings.html",
        store=store,
        success=request.args.get("success"),
        error=request.args.get("error"),
        shop_domain=shop,
        host=host,
        is_subscribed=user.is_subscribed if user else False,
    )


@shopify_bp.route("/settings/shopify/connect", methods=["POST"])
def connect_store():
    """Connect store via manual token - works in both embedded and standalone modes"""
    shop_url = request.form.get("shop_url", "").strip()
    access_token = request.form.get("access_token", "").strip()
    from shopify_utils import normalize_shop_url

    shop = request.args.get("shop") or request.form.get("shop") or request.args.get("shop", "")
    if shop:
        shop = normalize_shop_url(shop)

    host = request.args.get("host") or request.form.get("host") or request.args.get("host", "")

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
    except Exception as e:
        logger.error(f"Error finding user in connect_store: {e}", exc_info=True)
        from urllib.parse import urlencode

        params = {
            "error": "Authentication error occurred. Please try again.",
            "shop": shop or "",
            "host": host or "",
        }
        settings_url = (
            url_for("shopify.shopify_settings")
            + "?"
            + urlencode({k: v for k, v in params.items() if v})
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    if not user:
        logger.warning(f"Connect store: No user found via shop lookup")

        # CRITICAL FIX: Check Flask-Login session
        if current_user.is_authenticated:
            user = current_user
            logger.info(
                f"✅ Using authenticated current_user {user.id} for connect_store"
            )
        else:
            # Not authenticated at all
            from urllib.parse import urlencode

            params = {
                "error": "Please log in to connect your store.",
                "shop": shop or "",
                "host": host or "",
            }
            settings_url = (
                url_for("shopify.shopify_settings")
                + "?"
                + urlencode({k: v for k, v in params.items() if v})
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

        if "error" in result or "errors" in result:
            error_msg = result.get("error", "Token validation failed")
            if "errors" in result:
                error_msg = "; ".join(
                    [e.get("message", str(e)) for e in result["errors"]]
                )

            logger.warning(f"Access token test failed for {shop_url}: {error_msg}")

            # Check for specific error types
            if "401" in str(error_msg) or "unauthorized" in error_msg.lower():
                error_display = "Access token is invalid or expired. Please generate a new token from your Shopify admin."
            elif "403" in str(error_msg) or "forbidden" in error_msg.lower():
                error_display = "Access token lacks required permissions. Please ensure it has read_orders, read_products, and read_inventory permissions."
            else:
                error_display = f'Token validation failed: {error_msg}. Please use the "Quick Connect" OAuth method instead.'

            settings_url = url_for(
                "shopify.shopify_settings",
                error=error_display,
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)

        # Verify we got shop data
        shop_data = result.get("shop")
        if not shop_data or not shop_data.get("name"):
            logger.warning(f"Access token test returned no shop data for {shop_url}")
            settings_url = url_for(
                "shopify.shopify_settings",
                error="Access token validation failed - no shop data returned. Please check your token permissions.",
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)

        logger.info(f"Access token validated successfully for {shop_url}")

    except Exception as e:
        logger.error(f"Error validating access token: {e}", exc_info=True)
        error_msg = "Access token validation failed due to connection error. Please try the OAuth connection method instead."
        settings_url = url_for(
            "shopify.shopify_settings",
            error=error_msg,
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    # Check if user already has an active store
    existing_store = ShopifyStore.query.filter_by(
        user_id=user.id, is_active=True
    ).first()
    if existing_store:
        # Check if it's the same shop
        if existing_store.shop_url == shop_url:
            # Update existing store with new token
            try:
                from data_encryption import encrypt_access_token

                encrypted_token = encrypt_access_token(access_token)
                if encrypted_token is None:
                    logger.warning(
                        "Encryption failed for manual token, storing as plaintext"
                    )
                    encrypted_token = access_token

                existing_store.access_token = encrypted_token
                existing_store.is_active = True
                existing_store.is_installed = True
                existing_store.uninstalled_at = None
                db.session.commit()

                logger.info(f"Updated existing store connection for {shop_url}")
                settings_url = url_for(
                    "shopify.shopify_settings",
                    success="Store connection updated successfully!",
                    shop=shop,
                    host=host,
                )
                return safe_redirect(settings_url, shop=shop, host=host)
            except Exception as e:
                logger.error(f"Error updating existing store: {e}")
                db.session.rollback()
                settings_url = url_for(
                    "shopify.shopify_settings",
                    error="Failed to update store connection. Please try again.",
                    shop=shop,
                    host=host,
                )
                return safe_redirect(settings_url, shop=shop, host=host)
        else:
            # Different shop - user needs to disconnect first
            settings_url = url_for(
                "shopify.shopify_settings",
                error=f"You already have a connected store ({existing_store.shop_url}). Please disconnect it first to connect a different store.",
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)

    # Create new store connection
    try:
        from data_encryption import encrypt_access_token

        encrypted_token = encrypt_access_token(access_token)
        if encrypted_token is None:
            logger.warning("Encryption failed for manual token, storing as plaintext")
            encrypted_token = access_token

        new_store = ShopifyStore(
            user_id=user.id,
            shop_url=shop_url,
            access_token=encrypted_token,
            is_active=True,
            is_installed=True,
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

    except Exception as e:
        logger.error(f"Error creating store connection: {e}")
        db.session.rollback()
        settings_url = url_for(
            "shopify.shopify_settings",
            error="Failed to create store connection. Please try again.",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)


@shopify_bp.route("/settings/shopify/disconnect", methods=["POST"])
def disconnect_store():
    """Disconnect store - HARD CLEAR of all session data"""
    from flask_login import logout_user

    from shopify_utils import normalize_shop_url

    # Prioritize context from URL to survive iframe session blocks
    shop = request.args.get("shop") or request.form.get("shop") or session.get("shop_domain")
    if shop:
        shop = normalize_shop_url(shop)

    host = request.args.get("host") or request.form.get("host") or session.get("host")

    if not shop:
        logger.warning("Disconnect: No shop context found - redirecting with error")
        return redirect(url_for("shopify.shopify_settings", error="Shop context lost"))

    # Get authenticated user - PRIORITIZE current_user
    user = None
    try:
        if current_user.is_authenticated:
            user = current_user
            logger.info(f"Disconnect: Using authenticated user {user.id}")
        elif shop:
            # Try to find user from shop (for embedded apps)
            store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
            if store and store.user:
                user = store.user
                logger.info(f"Disconnect: Found user {user.id} via shop {shop}")
                
                # CRITICAL: If user is anonymous, log them in manually using the shop parameter context
                # This survives iframe session amnesia
                from flask_login import login_user
                login_user(user, remember=False)
                session["_user_id"] = user.id
                session["shop_domain"] = shop
                session.permanent = True
                logger.info(f"Disconnect: Manually logged in user {user.id} via shop context")
    except Exception as e:
        logger.error(f"Error finding user in disconnect_store: {e}", exc_info=True)
        db.session.rollback()
        # SELECTIVE CLEAR even on error - keep user logged in
        shopify_keys = [
            "current_shop",
            "access_token",
            "shop_domain",
            "shop_url",
            "host",
            "hmac",
        ]
        for key in shopify_keys:
            session.pop(key, None)
        return redirect(
            url_for(
                "shopify.shopify_settings",
                error="Authentication error occurred. Please try again.",
                shop=shop,
            )
        )

    if not user:
        logger.warning(f"Disconnect: No user found via shop lookup")

        # CRITICAL FIX: Check Flask-Login session
        if current_user.is_authenticated:
            user = current_user
            logger.info(
                f"✅ Using authenticated current_user {user.id} for disconnect_store"
            )
        else:
            # Not authenticated - clear Shopify keys and redirect
            shopify_keys = [
                "current_shop",
                "access_token",
                "shop_domain",
                "shop_url",
                "host",
                "hmac",
            ]
            for key in shopify_keys:
                session.pop(key, None)
            return redirect(
                url_for(
                    "shopify.shopify_settings",
                    error="Please log in to disconnect your store.",
                    shop=shop,
                )
            )

    # Find the user's active store
    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    if not store:
        logger.warning(f"Disconnect: No active store for user {user.id}")
        # SELECTIVE CLEAR - keep user logged in
        shopify_keys = [
            "current_shop",
            "access_token",
            "shop_domain",
            "shop_url",
            "host",
            "hmac",
        ]
        for key in shopify_keys:
            session.pop(key, None)
        return redirect(
            url_for(
                "shopify.shopify_settings",
                error="No active store found to disconnect.",
                shop=shop,
            )
        )

    shop_domain = store.shop_domain or store.shop_url

    try:
        # Disconnect the store - mark as inactive but keep token for potential reconnection
        store.is_active = False
        store.is_installed = False
        store.uninstalled_at = datetime.now(timezone.utc)
        store.charge_id = None
        # Don't clear access_token - it has a validator that prevents empty values
        # The is_active=False flag is sufficient to disconnect

        db.session.commit()
        logger.info(
            f"Store {store.shop_url} disconnected successfully for user {user.id}"
        )

        # SELECTIVE CLEAR: Remove only Shopify-specific session keys
        # Keep user logged in (preserve _user_id)
        shopify_keys = [
            "current_shop",
            "access_token",
            "shop_domain",
            "shop_url",
            "host",
            "hmac",
        ]
        for key in shopify_keys:
            session.pop(key, None)

        return redirect(
            url_for(
                "shopify.shopify_settings",
                success="Disconnected.",
                shop=shop_domain,
            )
        )

    except Exception as e:
        logger.error(
            f"Error disconnecting store for user {user.id}: {e}", exc_info=True
        )
        db.session.rollback()

        # SELECTIVE CLEAR even on error - keep user logged in
        shopify_keys = [
            "current_shop",
            "access_token",
            "shop_domain",
            "shop_url",
            "host",
            "hmac",
        ]
        for key in shopify_keys:
            session.pop(key, None)

        return redirect(
            url_for(
                "shopify.shopify_settings",
                error="Failed to disconnect store. Please try again.",
                shop=shop,
            )
        )
