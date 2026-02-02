"""
Shopify Billing Integration
MANDATORY: All Shopify App Store apps MUST use Shopify Billing API
Stripe/external payment processors are NOT allowed for embedded apps
"""

import os
from datetime import datetime

from flask import (
    Blueprint,
    Response,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from logging_config import logger
from models import ShopifyStore, User, db

billing_bp = Blueprint("billing", __name__)

# Shopify Billing API configuration
from config import SHOPIFY_API_VERSION

APP_URL = os.getenv("SHOPIFY_APP_URL", "https://employeesuite-production.onrender.com")


def safe_redirect(url, shop=None, host=None):
    """Safe redirect for embedded/standalone contexts - App Bridge compliant"""
    is_embedded = bool(host) or bool(shop) or request.args.get("embedded") == "1"
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
        return Response(redirect_html, mimetype="text/html")
    else:
        return redirect(url)


# Plan configuration (Production Prices: $99 and $297)
PLANS = {
    "pro": {
        "name": "Growth",
        "price": 99.00,
        "features": [
            "Inventory Intelligence Dashboard",
            "Smart Reorder Recommendations",
            "Dead Stock Alerts",
            "30-Day Sales Forecasting",
            "CSV Export Capable",
            "Up to 3 Store Connections",
            "Email Support",
        ],
    },
    "business": {
        "name": "Scale",
        "price": 297.00,
        "features": [
            "Everything in Growth",
            "Advanced Multi-Location Sync",
            "Automated Supplier Emails",
            "Custom Reporting Engine",
            "Unlimited Data History",
            "Priority 24/7 Support",
            "Dedicated Success Manager",
            "Early Access to Beta Features",
        ],
    },
}

SUBSCRIBE_HTML = """
<!DOCTYPE html>
<html>
<head>
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
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
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
            font-family: inherit;
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

            <!-- GROWTH Plan ($99) -->
            <div class="pricing-card featured">
                <span class="popular-badge">Most Popular</span>
                <div class="plan-name">Growth</div>
                <div class="plan-desc">Inventory Intelligence</div>
                <div class="plan-price">$99<span>/month</span></div>
                <ul class="plan-features">
                    <li>Inventory Intelligence Dashboard</li>
                    <li>Smart Reorder Recommendations</li>
                    <li>Dead Stock Alerts ($)</li>
                    <li>30-Day Sales Forecasting</li>
                    <li>CSV Exports</li>
                    <li>Up to 3 Store Connections</li>
                    <li>90 days data history</li>
                    <li>Email Support</li>
                </ul>
                <form method="POST" action="/billing/create-charge" style="margin:0;">
                    <input type="hidden" name="shop" value="{{ shop }}">
                    <input type="hidden" name="host" value="{{ host }}">
                    <input type="hidden" name="plan" value="pro">
                    <button type="submit" class="btn btn-primary">Start Free Trial</button>
                    <div style="text-align: center; margin-top: 8px; font-size: 12px; color: #6d7175;">No risk. Cancel anytime.</div>
                </form>
            </div>

            <!-- SCALE Plan ($297) -->
            <div class="pricing-card">
                <div class="plan-name">Scale</div>
                <div class="plan-desc">For high-volume merchants</div>
                <div class="plan-price">$297<span>/month</span></div>
                <ul class="plan-features">
                    <li>Everything in Growth</li>
                    <li>Advanced Multi-Location Sync</li>
                    <li>Automated Supplier Emails</li>
                    <li>Custom Reporting Engine</li>
                    <li>Unlimited Data History</li>
                    <li>Unlimited Stores</li>
                    <li>Priority 24/7 Support</li>
                    <li>Dedicated Success Manager</li>
                </ul>
                <form method="POST" action="/billing/create-charge" style="margin:0;">
                    <input type="hidden" name="shop" value="{{ shop }}">
                    <input type="hidden" name="host" value="{{ host }}">
                    <input type="hidden" name="plan" value="business">
                    <button type="submit" class="btn btn-primary">Start Free Trial</button>
                </form>
            </div>
        </div>

        {% if error %}
        <div style="max-width: 600px; margin: 32px auto 0; padding: 16px; background: #fff4f4; border: 1px solid #fecaca; border-radius: 8px; color: #d72c0d; text-align: center;">
            <strong>Note:</strong> {{ error }}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

SUCCESS_HTML = """
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
"""


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

        variables = {
            "name": f"Employee Suite {plan['name']}",
            "returnUrl": return_url,
            "test": test_mode,
            "trialDays": 7,  # Standard 7-day free trial
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
        charge_id = parse_gid(gid)

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
def subscribe():
    """Subscribe page - uses Shopify Billing API"""
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

    plan_type = request.args.get("plan", "pro")

    # Validate plan type
    if plan_type not in PLANS:
        plan_type = "pro"

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
        return render_template_string(
            SUBSCRIBE_HTML,
            trial_active=False,
            has_access=False,
            days_left=0,
            is_subscribed=False,
            shop=shop,
            host=host,
            has_store=False,
            plan=plan_type,
            plan_name=plan["name"],
            price=int(plan["price"]),
            features=plan["features"],
            error="Please connect your Shopify store first.",
        )

    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    has_store = store is not None and store.is_connected()

    if not shop and store:
        shop = store.shop_url

    trial_active = user.is_trial_active()
    has_access = user.has_access()
    days_left = (user.trial_ends_at - datetime.utcnow()).days if trial_active else 0

    error = request.args.get("error")
    if not has_store and not error:
        error = "No Shopify store connected"

    return render_template_string(
        SUBSCRIBE_HTML,
        trial_active=trial_active,
        has_access=has_access,
        days_left=days_left,
        is_subscribed=user.is_subscribed,
        shop=shop,
        host=host,
        has_store=has_store,
        plan=plan_type,
        plan_name=plan["name"],
        price=int(plan["price"]),
        features=plan["features"],
        error=error,
        config_api_key=os.getenv("SHOPIFY_API_KEY"),
    )


@billing_bp.route("/create-charge", methods=["POST"])
def create_charge():
    """Create a Shopify recurring charge"""
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

    plan_type = request.form.get("plan") or request.args.get("plan", "pro")

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
        logger.error(f"No active store found for user {user.id}")
        subscribe_url = url_for(
            "billing.subscribe",
            error="No Shopify store connected",
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)

    shop_url = store.shop_url

    if not store.is_connected():
        logger.error(f"Store {shop_url} not connected")
        settings_url = url_for(
            "shopify.shopify_settings",
            error="Store not connected. Please reconnect.",
            shop=shop_url,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop_url, host=host)

    access_token = store.get_access_token()

    if user.is_subscribed:
        dashboard_url = f"/dashboard?shop={shop_url}&host={host}"
        return safe_redirect(dashboard_url, shop=shop_url, host=host)

    return_url = (
        f"{APP_URL}/billing/confirm?shop={shop_url}&host={host}&plan={plan_type}"
    )

    result = create_recurring_charge(shop_url, access_token, return_url, plan_type)

    if not result.get("success"):
        error_msg = result.get("error", "Failed to create subscription")
        logger.error(f"Billing error for {shop_url}: {error_msg}")

        if (
            "owned by a shop" in error_msg.lower()
            or "must be migrated" in error_msg.lower()
        ):
            store.disconnect()
            db.session.commit()
            install_url = url_for("oauth.install", shop=shop_url, host=host)
            return render_template_string(f"""
            <!DOCTYPE html>
            <html><head><meta charset="utf-8"><title>Redirecting...</title>
            <script>window.location.href = '{install_url}';</script>
            </head><body><p>Redirecting...</p></body></html>
            """)

        formatted_error = format_billing_error(error_msg)
        return redirect(
            url_for(
                "billing.subscribe",
                error=formatted_error,
                shop=shop_url,
                host=host,
                plan=plan_type,
            )
        )

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
    from enhanced_models import PLAN_PRICES, SubscriptionPlan

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

    charge_id = request.args.get("charge_id")
    plan_type = request.args.get("plan", "pro")

    if not charge_id:
        logger.warning("No charge_id in billing confirm callback")
        subscribe_url = url_for(
            "billing.subscribe",
            error="Missing charge information",
            shop=shop,
            host=host,
            plan=plan_type,
        )
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
        subscribe_url = url_for(
            "billing.subscribe",
            error="Store not found",
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)

    shop_url = store.shop_url
    access_token = store.get_access_token()
    if not access_token:
        subscribe_url = url_for(
            "billing.subscribe",
            error="Store not properly connected.",
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)

    status_result = get_charge_status(shop_url, access_token, charge_id)

    if not status_result.get("success"):
        store.charge_id = None
        db.session.commit()
        subscribe_url = url_for(
            "billing.subscribe",
            error="Could not verify subscription.",
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)

    status = status_result.get("status", "")

    if status == "accepted":
        try:
            store = (
                ShopifyStore.query.with_for_update()
                .filter_by(shop_url=shop_url, user_id=user.id)
                .first()
            )
            if not store:
                db.session.rollback()
                subscribe_url = url_for(
                    "billing.subscribe",
                    error="Store not found",
                    shop=shop,
                    host=host,
                    plan=plan_type,
                )
                return safe_redirect(subscribe_url, shop=shop, host=host)

            locked_access_token = store.get_access_token()
            if not locked_access_token:
                db.session.rollback()
                subscribe_url = url_for(
                    "billing.subscribe",
                    error="Store not properly connected",
                    shop=shop,
                    host=host,
                    plan=plan_type,
                )
                return safe_redirect(subscribe_url, shop=shop, host=host)

            activate_result = activate_recurring_charge(
                shop_url, locked_access_token, charge_id
            )

            if activate_result.get("success"):
                user.is_subscribed = True
                store.charge_id = str(charge_id)

                # Create/update SubscriptionPlan
                plan_price = PLAN_PRICES.get(plan_type, 29.00)
                existing_plan = SubscriptionPlan.query.filter_by(
                    user_id=user.id
                ).first()
                if existing_plan:
                    existing_plan.plan_type = plan_type
                    existing_plan.price_usd = plan_price
                    existing_plan.charge_id = str(charge_id)
                    existing_plan.status = "active"
                    existing_plan.cancelled_at = None
                    existing_plan.multi_store_enabled = plan_type == "business"
                    existing_plan.automated_reports_enabled = plan_type == "business"
                    existing_plan.scheduled_delivery_enabled = plan_type == "business"
                else:
                    new_plan = SubscriptionPlan(
                        user_id=user.id,
                        plan_type=plan_type,
                        price_usd=plan_price,
                        charge_id=str(charge_id),
                        status="active",
                        multi_store_enabled=(plan_type == "business"),
                        automated_reports_enabled=(plan_type == "business"),
                        scheduled_delivery_enabled=(plan_type == "business"),
                    )
                    db.session.add(new_plan)

                db.session.commit()
                logger.info(f"Subscription activated for {shop_url}, plan: {plan_type}")

                return render_template_string(SUCCESS_HTML, shop=shop_url, host=host)
            else:
                db.session.rollback()
                logger.error(
                    f"Failed to activate charge: {activate_result.get('error')}"
                )
                subscribe_url = url_for(
                    "billing.subscribe",
                    error="Failed to activate subscription",
                    shop=shop,
                    host=host,
                    plan=plan_type,
                )
                return safe_redirect(subscribe_url, shop=shop, host=host)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in charge activation: {e}")
            subscribe_url = url_for(
                "billing.subscribe",
                error="Error processing subscription",
                shop=shop,
                host=host,
                plan=plan_type,
            )
            return safe_redirect(subscribe_url, shop=shop, host=host)

    elif status == "active":
        user.is_subscribed = True
        store.charge_id = str(charge_id)
        db.session.commit()
        return render_template_string(SUCCESS_HTML, shop=shop_url, host=host)

    elif status == "declined":
        logger.info(f"Merchant declined subscription for {shop_url}")
        subscribe_url = url_for(
            "billing.subscribe",
            error="Subscription was declined",
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)

    else:
        logger.warning(f"Unexpected charge status '{status}' for {shop_url}")
        subscribe_url = url_for(
            "billing.subscribe",
            error=f"Subscription status: {status}",
            shop=shop,
            host=host,
            plan=plan_type,
        )
        return safe_redirect(subscribe_url, shop=shop, host=host)


@billing_bp.route("/billing/cancel", methods=["POST"])
def cancel_subscription():
    """Cancel Shopify subscription"""
    import requests

    shop = request.form.get("shop") or request.args.get("shop", "")
    host = request.form.get("host") or request.args.get("host", "")

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
        settings_url = url_for(
            "shopify.shopify_settings",
            error="Authentication required",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

    store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
    if not store or not store.charge_id:
        settings_url = url_for(
            "shopify.shopify_settings",
            error="No active subscription found",
            shop=shop,
            host=host,
        )
        return safe_redirect(settings_url, shop=shop, host=host)

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
            settings_url = url_for(
                "shopify.shopify_settings",
                success="Subscription cancelled",
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)
        else:
            logger.error(f"Failed to cancel subscription: {response.status_code}")
            settings_url = url_for(
                "shopify.shopify_settings",
                error="Failed to cancel subscription",
                shop=shop,
                host=host,
            )
            return safe_redirect(settings_url, shop=shop, host=host)
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        settings_url = url_for(
            "shopify.shopify_settings", error=str(e), shop=shop, host=host
        )
        return safe_redirect(settings_url, shop=shop, host=host)


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


# Billing status formatting utilities
def format_billing_error(error_msg):
    """Format common Shopify billing errors into user-friendly messages"""
    error_lower = error_msg.lower()

    if "422" in error_msg or "unprocessable" in error_lower:
        if "owned by a shop" in error_lower or "must be migrated" in error_lower:
            return "App ownership migration required in Shopify Partners dashboard."
        return f"Shopify could not process this subscription: {error_msg[:100]}"
    return f"Billing error: {error_msg[:150]}"
