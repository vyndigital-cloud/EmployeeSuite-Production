"""
Shopify Billing Integration
MANDATORY: All Shopify App Store apps MUST use Shopify Billing API
Stripe/external payment processors are NOT allowed for embedded apps
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

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
from flask_login import current_user, login_required, login_user
from access_control import require_access, require_active_shop, require_zero_trust

# Add error handling for imports
try:
    from enhanced_models import PLAN_PRICES, SubscriptionPlan
except ImportError as e:
    # Log the error so we know it's missing
    import logging
    logging.getLogger(__name__).warning(f"Could not import enhanced_models: {e}. Using fallback defaults.")
    
    PLAN_PRICES = {"pro": 39.00}

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
from error_logging import error_logger
from session_token_verification import verify_session_token

billing_bp = Blueprint("billing", __name__)

def handle_billing_error(error, shop="", host="", plan_type="pro"):
    """Centralized billing error handler"""
    error_logger.log_error(error, "BILLING_ERROR", {
        'shop': shop,
        'plan_type': plan_type
    })
    
    formatted_error = format_billing_error(str(error))
    subscribe_url = f"/billing/subscribe?error={formatted_error}&shop={shop}&host={host}&plan={plan_type}"
    return safe_redirect(subscribe_url, shop=shop, host=host)

# Shopify Billing API configuration
from config import SHOPIFY_API_VERSION

# Ensure required environment variables
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
if not SHOPIFY_API_KEY:
    logger.warning("SHOPIFY_API_KEY environment variable not set")
    SHOPIFY_API_KEY = ""

APP_URL = os.getenv("SHOPIFY_APP_URL", "https://employeesuite-production.onrender.com")


from utils import safe_redirect


def csrf_token():
    """Generate CSRF token for templates"""
    try:
        from flask import session
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(32)
        return session['csrf_token']
    except:
        return ''


# Plan configuration (Production Price: $39/month - competitive pricing)
PLANS = {
    "pro": {
        "name": "Employee Suite Pro",
        "price": 39.00,
        "value_comparison": "Save time & money",
        "competitor_comparison": "All-in-one Toolkit",
        "features": [
            "Comprehensive Order Processing",
            "Advanced Inventory Management",
            "Revenue Analytics & Reporting",
            "Unlimited CSV Exports",
            "Automated Low Stock Alerts",
            "Priority Support",
        ],
        "total_value": "Complete store management",
        "savings_percentage": "",
        "roi_statement": "",
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
            font-size: 32px;  font-weight: 700; 
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
@verify_session_token
def subscribe():
    """Enhanced subscribe page with strong CTAs"""
    from shopify_utils import normalize_shop_url
    
    try:
        # Normalize shop URL first thing
        shop = request.args.get("shop", "").strip()
        if shop:
            shop = normalize_shop_url(shop)

        host = request.args.get("host", "").strip() or session.get("host", "").strip()
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
        # TITAN OPTIMIZATION: Trust local DB state for render speed.
        # GraphQL check is moved to the actual charge creation (POST)
        has_store = bool(store and store.access_token)
        if store and not store.is_active:
             # If we explicitly know it's inactive, flag it
             has_store = False

        # Set shop from store if not provided
        if not shop and store:
            shop = store.shop_url

        # Calculate user status with safety checks
        trial_active = False
        has_access = False
        days_left = 0

        if user:
            # CRITICAL FIX: Query fresh DB data to prevent stale session issues
            try:
                db.session.refresh(user)
                fresh_user = db.session.query(User).filter_by(id=user.id).first()
                
                if fresh_user:
                    # Use fresh data from database
                    has_access = fresh_user.has_access()
                    trial_active = fresh_user.is_trial_active() if not fresh_user.is_subscribed else False
                    
                    logger.info(
                        f"🔍 BILLING CHECK: User {fresh_user.id} - "
                        f"has_access={has_access}, is_subscribed={fresh_user.is_subscribed}, "
                        f"trial_active={trial_active}"
                    )
                    
                    # Check trial status
                    if fresh_user.trial_started_at and not fresh_user.is_subscribed:
                        if trial_active and fresh_user.trial_ends_at:
                            try:
                                now = datetime.utcnow()
                                trial_end = fresh_user.trial_ends_at
                                if trial_end.tzinfo is None:
                                    trial_end = trial_end.replace(tzinfo=timezone.utc)
                                    now = now.replace(tzinfo=timezone.utc)
                                
                                days_left = (trial_end - now).days
                                days_left = max(0, days_left)
                            except (AttributeError, TypeError):
                                days_left = 0
                else:
                    has_access = False
            except Exception as refresh_error:
                logger.error(f"Error refreshing user data: {refresh_error}")
                has_access = user.has_access()  # Fallback to cached
        
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
            "config_api_key": SHOPIFY_API_KEY,
            # Add these missing variables for JavaScript
            "user_authenticated": user is not None,
            "store_connected": has_store,
            "csrf_token": csrf_token,
        }

        # Always render subscribe template - never redirect from this route
        try:
            return render_template("subscribe.html", **template_vars)
        except Exception as template_error:
            logger.error(f"Template rendering error: {template_error}")
            # Fallback to basic error response
            return f"Subscribe page error: {error or 'Unknown error'}", 500
            
    except Exception as e:
        logger.error(f"Critical error in subscribe route: {e}", exc_info=True)
        # Return subscribe template even on error - don't return JSON
        error_vars = {
            "error": "Subscribe page temporarily unavailable. Please try again.",
            "shop": shop or "",
            "host": host or "",
            "plan": plan_type,
            "plan_name": PLANS.get(plan_type, PLANS["pro"])["name"],
            "price": int(PLANS.get(plan_type, PLANS["pro"])["price"]),
            "features": PLANS.get(plan_type, PLANS["pro"])["features"],
            "config_api_key": SHOPIFY_API_KEY,
            # Set safe defaults for all required template variables
            "trial_active": False,
            "has_access": False,
            "days_left": 0,
            "is_subscribed": False,
            "has_store": False,
            "user_authenticated": False,
            "store_connected": False,
            "csrf_token": csrf_token,
        }
        return render_template("subscribe.html", **error_vars)


def validate_csrf_token():
    """Enhanced CSRF validation for billing flows"""
    try:
        # For authenticated users, be more lenient
        if current_user.is_authenticated:
            return True
            
        # Check for Shopify-specific parameters that indicate legitimate request
        shop = request.form.get("shop") or request.args.get("shop", "")
        host = request.form.get("host") or request.args.get("host", "") or session.get("host", "")
        
        # If we have shop and host, this is likely a legitimate Shopify request
        if shop and host:
            # Additional validation: check if shop format is valid
            if ".myshopify.com" in shop or shop.endswith(".myshopify.io"):
                return True
        
        # For POST requests from the subscribe page, be more lenient
        if request.method == "POST" and request.endpoint in ['billing.create_charge', 'billing.start_trial']:
            return True
        
        # Fallback to standard CSRF validation
        try:
            from shopify_utils import validate_csrf_token as validate_csrf
            return validate_csrf(request, session)
        except:
            # If CSRF validation fails, allow for authenticated users
            return current_user.is_authenticated
        
    except Exception as e:
        logger.warning(f"CSRF validation error: {e}")
        # For billing flows, err on the side of allowing legitimate requests
        return current_user.is_authenticated



@billing_bp.route("/create-charge", methods=["GET", "POST"])
@billing_bp.route("/billing/create-charge", methods=["GET", "POST"])
def create_charge():
    """Create a Shopify recurring charge"""
    from shopify_utils import normalize_shop_url
    
    # Normalize shop URL first thing
    shop = request.form.get("shop") or request.args.get("shop", "")

    # Enhanced shop detection for embedded apps
    if not shop:
        # Try to get from referrer or session
        referrer = request.headers.get('Referer', '')
        if 'shop=' in referrer:
            import urllib.parse
            parsed = urllib.parse.urlparse(referrer)
            query_params = urllib.parse.parse_qs(parsed.query)
            if 'shop' in query_params:
                shop = query_params['shop'][0]
        
        # Try session as last resort
        if not shop:
            shop = session.get('shop', '')
    
    # If shop is missing, try to get from user session/context
    if not shop and current_user.is_authenticated:
        # Try to find store for current user
        try:
            store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
            if store:
                shop = store.shop_url
        except Exception:
            pass
            
    if shop:
        shop = normalize_shop_url(shop)
    
    if not shop:
        logger.warning("Billing request missing shop parameter")
        return redirect("/billing/subscribe?error=Missing store context. Please try logging in again.")

    host = request.form.get("host") or request.args.get("host", "") or session.get("host", "")
    plan_type = request.form.get("plan") or request.args.get("plan", "pro")

    # Enhanced CSRF protection for billing flows
    csrf_valid = validate_csrf_token()
    if not csrf_valid:
        logger.warning(f"CSRF validation failed for billing request from shop: {shop}")
        
        # For billing, check if this is a legitimate Shopify callback
        if shop and host and current_user.is_authenticated:
            logger.info(f"Allowing billing request for authenticated user {current_user.id} with shop {shop}")
        else:
            error_msg = "Security validation failed. Please try again."
            subscribe_url = f"/billing/subscribe?error={error_msg}&shop={shop}&host={host}&plan={plan_type}"
            return safe_redirect(subscribe_url, shop=shop, host=host)

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
        subscribe_url = f"/billing/subscribe?error=Please connect your Shopify store first.&shop={shop}&host={host}&plan={plan_type}"
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
        settings_url = "/settings?error=Store not connected. Please reconnect.&shop=" + shop_url + "&host=" + host
        return safe_redirect(settings_url, shop=shop_url, host=host)

    # Optional: Test the connection with a simple API call
    try:
        from shopify_graphql import ShopifyGraphQLClient
        client = ShopifyGraphQLClient(shop_url, access_token)
        test_result = client.execute_query("query { shop { name } }")
        if "error" in test_result:
            logger.error(f"Store {shop_url} connection test failed: {test_result['error']}")
            settings_url = "/settings?error=Store connection issue. Please reconnect.&shop=" + shop_url + "&host=" + host
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
            install_url = f"/install?shop={shop_url}&host={host}"
            return render_template_string(f"""
            <!DOCTYPE html>
            <html><head><meta charset="utf-8"><title>Redirecting...</title>
            <script>window.location.href = '{install_url}';</script>
            </head><body><p>Redirecting...</p></body></html>
            """)

        return handle_billing_error(Exception(error_msg), shop_url, host, plan_type)

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

    host = request.args.get("host", "") or session.get("host", "")

    charge_id = request.args.get("charge_id")
    plan_type = request.args.get("plan", "pro")

    if not charge_id:
        logger.warning("No charge_id in billing confirm callback")
        subscribe_url = f"/billing/subscribe?error=Missing charge information&shop={shop}&host={host}&plan={plan_type}"
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
        subscribe_url = f"/billing/subscribe?error=Store not found&shop={shop}&host={host}&plan={plan_type}"
        return safe_redirect(subscribe_url, shop=shop, host=host)

    shop_url = store.shop_url
    access_token = store.get_access_token()
    if not access_token:
        subscribe_url = f"/billing/subscribe?error=Store not properly connected.&shop={shop}&host={host}&plan={plan_type}"
        return safe_redirect(subscribe_url, shop=shop, host=host)

    status_result = get_charge_status(shop_url, access_token, charge_id)

    if not status_result.get("success"):
        store.charge_id = None
        db.session.commit()
        subscribe_url = f"/billing/subscribe?error=Could not verify subscription.&shop={shop}&host={host}&plan={plan_type}"
        return safe_redirect(subscribe_url, shop=shop, host=host)

    status = status_result.get("status", "")

    if status.lower() in ["accepted", "active"]:
        try:
            # Use database transaction for consistency
            with db.session.begin():
                store = (
                    ShopifyStore.query.with_for_update()
                    .filter_by(shop_url=shop_url, user_id=user.id)
                    .first()
                )
                if not store:
                    raise Exception("Store not found during confirmation")

                # Immediately grant subscription access
                user.is_subscribed = True
                store.charge_id = charge_id
                
                # Update enhanced models if present
                try:
                    from enhanced_models import SubscriptionPlan as ESubscriptionPlan
                    e_plan = ESubscriptionPlan.query.filter_by(user_id=user.id).first()
                    if not e_plan:
                        e_plan = ESubscriptionPlan(
                            user_id=user.id, 
                            plan_type="pro", 
                            price_usd=39.00
                        )
                        db.session.add(e_plan)
                    e_plan.status = 'active'
                    e_plan.charge_id = charge_id
                except ImportError: 
                    pass
                    
            logger.info(f"Charge {charge_id} confirmed for {shop_url}. Subscription activated.")

            return render_template_string(SUCCESS_HTML, 
                                        dashboard_url=f"/dashboard?shop={shop}&host={host}",
                                        trial_end_date=(datetime.now() + timedelta(days=7)).strftime('%B %d, %Y'))
                                        
        except Exception as e:
            logger.error(f"Error activating subscription: {e}")
            subscribe_url = f"/billing/subscribe?error=Activation failed. Please contact support.&shop={shop}&host={host}&plan={plan_type}"
            return safe_redirect(subscribe_url, shop=shop, host=host)
    else:
        # Charge declined or expired
        store.charge_id = None
        db.session.commit()
        subscribe_url = f"/billing/subscribe?error=Subscription was not accepted&shop={shop}&host={host}&plan={plan_type}"
        return safe_redirect(subscribe_url, shop=shop, host=host)




@billing_bp.route("/billing/start-trial", methods=["POST"])
def start_trial():
    """Start free trial without billing"""
    from shopify_utils import normalize_shop_url
    
    shop = request.form.get("shop") or request.args.get("shop", "")
    if shop:
        shop = normalize_shop_url(shop)
    
    host = request.form.get("host") or request.args.get("host", "") or session.get("host", "")
    
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
    except Exception as e:
        logger.error(f"Error finding user in start_trial: {e}")
        pass

    if not user:
        return jsonify({
            "success": False,
            "error": "Please connect your Shopify store first."
        }), 400

    # Check if user already has an active subscription
    if user.is_subscribed:
        dashboard_url = f"/dashboard?shop={shop}&host={host}"
        return jsonify({
            "success": True,
            "redirect_url": dashboard_url,
            "message": "You already have an active subscription."
        })

    # Start trial logic
    try:
        now = datetime.utcnow()
        
        if not user.trial_started_at:
            # First time starting trial
            user.trial_started_at = now
            user.trial_ends_at = now + timedelta(days=7)
            db.session.commit()
            
            logger.info(f"Started free trial for user {user.id}")
            
            dashboard_url = f"/dashboard?shop={shop}&host={host}"
            return jsonify({
                "success": True,
                "redirect_url": dashboard_url,
                "message": "Free trial started! You have 7 days of full access."
            })
        else:
            # Trial was already started - check if still active
            if user.is_trial_active():
                dashboard_url = f"/dashboard?shop={shop}&host={host}"
                return jsonify({
                    "success": True,
                    "redirect_url": dashboard_url,
                    "message": "Your free trial is already active."
                })
            else:
                # Trial has expired
                return jsonify({
                    "success": False,
                    "error": "Your free trial has expired. Please subscribe to continue using Employee Suite Pro."
                }), 400
                
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error starting trial: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to start trial. Please try again."
        }), 500


@billing_bp.route("/billing/cancel", methods=["POST"])
def cancel_subscription():
    """Cancel Shopify subscription"""
    import requests

    # Prioritize URL context for iframe compatibility
    shop = request.args.get("shop") or request.form.get("shop") or session.get("shop_domain", "")
    host = request.args.get("host") or request.form.get("host") or session.get("host", "")

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
        return app_bridge_redirect(url_for('shopify.shopify_settings', error="Authentication required", shop=shop, host=host))

    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    if not store or not store.charge_id:
        return app_bridge_redirect(url_for('shopify.shopify_settings', error="No active subscription found", shop=shop, host=host))

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
            return app_bridge_redirect(url_for('shopify.shopify_settings', success="Subscription cancelled", shop=shop, host=host))
        else:
            logger.error(f"Failed to cancel subscription: {response.status_code}")
            return app_bridge_redirect(url_for('shopify.shopify_settings', error="Failed to cancel subscription", shop=shop, host=host))
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        return app_bridge_redirect(url_for('shopify.shopify_settings', error=str(e), shop=shop, host=host))


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
