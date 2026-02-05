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
from shopify_utils import normalize_shop_url

shopify_bp = Blueprint("shopify", __name__)


from utils import safe_redirect



from flask import render_template

@shopify_bp.route("/settings/shopify")
def shopify_settings():
    """Shopify settings page - works in both embedded and standalone modes"""

    from shopify_utils import normalize_shop_url
    
    # Normalize shop URL first thing
    shop = request.args.get("shop", "")
    if shop:
        shop = normalize_shop_url(shop)

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
    except Exception as e:
        logger.error(f"Error finding user in shopify_settings: {e}", exc_info=True)
        # Continue with user=None, will redirect to appropriate auth flow

    # If no user found, redirect to login (don't redirect to install - causes loops)
    if not user:
        # Redirect to login for both embedded and standalone
        from flask import redirect, url_for
        return redirect(url_for("auth.login"))

    # Get user's store
    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()

    # Pass shop and host to template for links, and user subscription status
    return render_template(
        "settings.html",
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
    from shopify_utils import normalize_shop_url
    
    shop = request.form.get("shop") or request.args.get("shop", "")
    if shop:
        shop = normalize_shop_url(shop)

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
    except Exception as e:
        logger.error(f"Error finding user in connect_store: {e}", exc_info=True)
        from urllib.parse import urlencode
        params = {
            "error": "Authentication error occurred. Please try again.",
            "shop": shop or "",
            "host": host or ""
        }
        settings_url = url_for("shopify.shopify_settings") + '?' + urlencode({k: v for k, v in params.items() if v})
        return safe_redirect(settings_url, shop=shop, host=host)

    if not user:
        from urllib.parse import urlencode
        params = {
            "error": "Authentication required",
            "shop": shop or "",
            "host": host or ""
        }
        settings_url = url_for("shopify.shopify_settings") + '?' + urlencode({k: v for k, v in params.items() if v})
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
            logger.warning(f"Access token test failed for {shop_url}: {error_msg}")
            settings_url = url_for(
                "shopify.shopify_settings",
                error=f'Access token validation failed: {error_msg}. Please use the "Quick Connect" OAuth method instead.',
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
                error="Access token validation failed - no shop data returned. Please check your token.",
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)
            
        logger.info(f"Access token validated successfully for {shop_url}")

    except Exception as e:
        logger.error(f"Error validating access token: {e}", exc_info=True)
        settings_url = url_for(
            "shopify.shopify_settings",
            error="Access token validation failed. Please use the OAuth connection method instead.",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

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
    from shopify_utils import normalize_shop_url
    
    shop = request.form.get("shop") or request.args.get("shop", "")
    if shop:
        shop = normalize_shop_url(shop)

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
    except Exception as e:
        logger.error(f"Error finding user in disconnect_store: {e}", exc_info=True)
        settings_url = url_for(
            "shopify.shopify_settings",
            error="Authentication error occurred. Please try again.",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

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
            store.is_active = False
            store.is_installed = False
            store.uninstalled_at = datetime.now(timezone.utc)
            store.charge_id = None
            # Clear access token to force reconnection
            store.access_token = ""
            
            db.session.commit()
            logger.info(f"Store {store.shop_url} disconnected for user {user.id}")
            
            settings_url = url_for(
                "shopify.shopify_settings",
                success="Store disconnected successfully! You can now reconnect with the new Partners app.",
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)
        except Exception as e:
            logger.error(f"Error disconnecting store: {e}", exc_info=True)
            db.session.rollback()
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

    from shopify_utils import normalize_shop_url
    
    shop = request.form.get("shop") or request.args.get("shop", "")
    if shop:
        shop = normalize_shop_url(shop)

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
    except Exception as e:
        logger.error(f"Error finding user in cancel_subscription: {e}", exc_info=True)
        settings_url = url_for(
            "shopify.shopify_settings",
            error="Authentication error occurred. Please try again.",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

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
                logger.error(f"Failed to send cancellation email: {e}", exc_info=True)

            settings_url = url_for(
                "shopify.shopify_settings",
                success="Subscription cancelled successfully. You will retain access until the end of your billing period.",
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Failed to cancel Shopify subscription: {error_msg}")
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
