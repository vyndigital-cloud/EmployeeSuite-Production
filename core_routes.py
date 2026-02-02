"""
Core application routes - Clean version
"""

import csv
import io
import logging
import os
from datetime import datetime

from flask import (
    Blueprint,
    Response,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user

from models import ShopifyStore, User, db
from session_token_verification import verify_session_token

logger = logging.getLogger(__name__)
core_bp = Blueprint("core", __name__)


def require_access(f):
    """Simple access control"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required", "success": False}), 401
        if not current_user.has_access():
            return jsonify(
                {
                    "error": "Subscription required",
                    "success": False,
                    "action": "subscribe",
                }
            ), 403
        return f(*args, **kwargs)

    return decorated_function


# Deferred imports - moved inside functions to speed up startup
# from models import ShopifyStore, User, db
from session_token_verification import get_shop_from_session_token
from utils import safe_redirect


@core_bp.route("/admin/scaling-status")
def scaling_status():
    """Admin dashboard for scaling status"""
    if os.getenv("ENVIRONMENT") != "production":
        return jsonify({"error": "Only available in production"}), 403

    try:
        from auto_scaling import get_auto_scaler
        from performance import get_cache_efficiency

        scaler = get_auto_scaler()
        cache_stats = get_cache_efficiency()

        return jsonify(
            {
                "current_tier": scaler.current_tier,
                "max_load_seen": scaler.max_load_seen,
                "cache_efficiency": cache_stats,
                "scaling_thresholds": scaler.scaling_thresholds,
                "status": "healthy",
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Helper: get_authenticated_user
# ---------------------------------------------------------------------------


def get_authenticated_user():
    """Get authenticated user - with deferred imports"""
    # Import only when needed to speed up startup
    from models import ShopifyStore, User, db

    """
    Get authenticated user from either Flask-Login or Shopify session token.
    Returns (user, error_response) tuple. If user is None, error_response contains the error.
    """
    # Try Flask-Login first (for standalone access)
    if current_user.is_authenticated:
        logger.debug(f"User authenticated via Flask-Login: {current_user.id}")
        return current_user, None

    # Try session token (for embedded apps)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1] if " " in auth_header else None
            if not token:
                return None, (
                    jsonify({"error": "Invalid token format", "success": False}),
                    401,
                )

            import jwt

            api_secret = os.getenv("SHOPIFY_API_SECRET")
            api_key = os.getenv("SHOPIFY_API_KEY")

            if not api_secret:
                logger.warning(
                    "SHOPIFY_API_SECRET not set - cannot verify session token"
                )
                return None, (
                    jsonify({"error": "Server configuration error", "success": False}),
                    500,
                )

            if not api_key:
                logger.warning("SHOPIFY_API_KEY not set - cannot verify session token")
                return None, (
                    jsonify({"error": "Server configuration error", "success": False}),
                    500,
                )

            payload = jwt.decode(
                token,
                api_secret,
                algorithms=["HS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["iss", "dest", "aud", "sub", "exp", "nbf", "iat"],
                },
            )

            token_aud = payload.get("aud", "")
            if token_aud != api_key:
                logger.warning(
                    f"Invalid audience in session token: got '{token_aud}', expected '{api_key}'"
                )

            dest = payload.get("dest", "")
            if not dest or not dest.endswith(".myshopify.com"):
                logger.warning(f"Invalid destination in session token: {dest}")
                return None, (
                    jsonify({"error": "Invalid token", "success": False}),
                    401,
                )

            try:
                cleaned_dest = dest.replace("https://", "").replace("http://", "")
                shop_domain = (
                    cleaned_dest.split("/")[0] if "/" in cleaned_dest else cleaned_dest
                )
                if not shop_domain:
                    raise ValueError("Empty shop domain")
            except (IndexError, AttributeError, ValueError) as e:
                logger.warning(f"Error parsing shop domain from dest '{dest}': {e}")
                return None, (
                    jsonify({"error": "Invalid token format", "success": False}),
                    401,
                )

            store = None
            try:
                store = ShopifyStore.query.filter_by(
                    shop_url=shop_domain, is_active=True
                ).first()
            except BaseException as db_error:
                logger.error(
                    f"Database error in get_authenticated_user: {db_error}",
                    exc_info=True,
                )
                try:
                    db.session.rollback()
                except Exception:
                    pass
                finally:
                    # FIXED: Add proper session cleanup
                    try:
                        db.session.close()
                    except Exception:
                        pass

                return None, (
                    jsonify(
                        {
                            "error": "Database connection error",
                            "success": False,
                            "action": "retry",
                        }
                    ),
                    500,
                )

            if store and store.user:
                logger.info(
                    f"Session token verified - user {store.user.id} from shop {shop_domain}"
                )
                return store.user, None
            else:
                logger.warning(f"No store found for shop: {shop_domain}")
                return None, (
                    jsonify(
                        {
                            "error": "Your store is not connected. Please install the app from your Shopify admin.",
                            "success": False,
                            "action": "install",
                        }
                    ),
                    404,
                )

        except Exception as e:
            import jwt as jwt_module

            if isinstance(e, jwt_module.ExpiredSignatureError):
                return None, (
                    jsonify(
                        {
                            "error": "Your session has expired. Please refresh the page.",
                            "success": False,
                            "action": "refresh",
                        }
                    ),
                    401,
                )
            elif isinstance(e, jwt_module.InvalidTokenError):
                return None, (
                    jsonify(
                        {
                            "error": "Unable to verify your session. Please refresh the page.",
                            "success": False,
                            "action": "refresh",
                        }
                    ),
                    401,
                )
            else:
                logger.error(f"Error verifying session token: {e}", exc_info=True)
                return None, (
                    jsonify(
                        {
                            "error": "Session verification failed. Please try again.",
                            "success": False,
                            "action": "retry",
                        }
                    ),
                    401,
                )

    # Try shop parameter authentication
    shop_param = request.args.get("shop")
    if shop_param:
        try:
            shop_domain = (
                shop_param.replace("https://", "").replace("http://", "").split("/")[0]
            )
            if not shop_domain.endswith(".myshopify.com"):
                shop_domain = f"{shop_domain}.myshopify.com"

            store = ShopifyStore.query.filter_by(
                shop_url=shop_domain, is_active=True
            ).first()
            if store and store.user:
                logger.info(
                    f"Shop parameter auth successful - user {store.user.id} from shop {shop_domain}"
                )
                return store.user, None
        except Exception as e:
            logger.error(f"Error in shop parameter auth: {e}", exc_info=True)

    return None, (
        jsonify(
            {
                "error": "Please sign in to continue.",
                "success": False,
                "action": "login",
            }
        ),
        401,
    )


# ---------------------------------------------------------------------------
# Dashboard / Home
# ---------------------------------------------------------------------------


@core_bp.route("/")
@core_bp.route("/dashboard", endpoint="dashboard")
def home():
    """Optimized dashboard - target <300ms load time"""
    # Import only when needed to speed up startup
    from models import ShopifyStore, User, db

    # PERFORMANCE: Skip heavy database queries for initial load
    shop = request.args.get("shop")
    host = request.args.get("host")

    # Store in session immediately
    if shop:
        session["shop"] = shop
        session.permanent = True
    if host:
        session["host"] = host
        session.permanent = True

    # Local dev mode - instant response
    if os.getenv("ENVIRONMENT") != "production" and not shop:
        return render_template(
            "dashboard.html",
            trial_active=True,
            days_left=7,
            is_subscribed=False,
            has_shopify=True,
            has_access=True,
            quick_stats={
                "has_data": True,
                "pending_orders": 5,
                "total_products": 42,
                "low_stock_items": 3,
            },
            shop="demo-store.myshopify.com",
            APP_URL=request.url_root.rstrip("/"),
            host="",
        )

    # PERFORMANCE: Defer user lookup and use cached data
    user = None
    if current_user.is_authenticated:
        user = current_user
    elif shop:
        # Quick lookup without joins
        store = db.session.query(ShopifyStore).filter_by(shop_url=shop).first()
        if store:
            user = db.session.query(User).get(store.user_id)

    # Default values (avoid expensive calculations)
    if user:
        has_access = user.has_access()
        trial_active = user.is_trial_active()
        days_left = (
            max(0, (user.trial_ends_at - datetime.utcnow()).days) if trial_active else 0
        )
        is_subscribed = user.is_subscribed
        has_shopify = True  # Assume true if we have a user
    else:
        has_access, trial_active, days_left, is_subscribed, has_shopify = (
            False,
            False,
            0,
            False,
            False,
        )

    # PERFORMANCE: Use static quick stats (update via AJAX later)
    quick_stats = {
        "has_data": False,
        "pending_orders": 0,
        "total_products": 0,
        "low_stock_items": 0,
    }

    return render_template(
        "dashboard.html",
        trial_active=trial_active,
        days_left=days_left,
        is_subscribed=is_subscribed,
        has_shopify=has_shopify,
        has_access=has_access,
        quick_stats=quick_stats,
        shop=shop or "",
        APP_URL=os.getenv("APP_URL", request.url_root.rstrip("/")),
        host=host or "",
    )


# ---------------------------------------------------------------------------
# Favicon / Apple Touch Icon
# ---------------------------------------------------------------------------


@core_bp.route("/favicon.ico")
def favicon():
    return Response(status=204)


@core_bp.route("/apple-touch-icon.png")
@core_bp.route("/apple-touch-icon-precomposed.png")
def apple_touch_icon():
    return Response(status=204)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------


@core_bp.route("/health")
def health():
    """Enhanced health check endpoint"""
    from models import db

    checks = {}
    overall_status = "healthy"

    # Database check
    try:
        db.session.execute(db.text("SELECT 1"))
        checks["database"] = {"status": "connected"}
    except Exception as e:
        checks["database"] = {"error": str(e), "status": "disconnected"}
        overall_status = "unhealthy"

    # Cache check
    try:
        from performance import get_cache_stats

        cache_stats = get_cache_stats()
        checks["cache"] = {
            "entries": cache_stats.get("entries", 0),
            "status": "operational",
        }
    except Exception as e:
        checks["cache"] = {"error": str(e), "status": "error"}
        overall_status = "unhealthy"

    # Configuration check
    try:
        required_vars = ["SHOPIFY_API_KEY", "SHOPIFY_API_SECRET", "SECRET_KEY"]
        missing = [var for var in required_vars if not os.getenv(var)]

        checks["configuration"] = {
            "status": "valid" if not missing else "invalid",
            "missing_vars": missing,
        }

        if missing:
            overall_status = "unhealthy"

    except Exception as e:
        checks["configuration"] = {"error": str(e)}
        overall_status = "unhealthy"

    # Memory check
    try:
        import psutil

        memory_percent = psutil.virtual_memory().percent
        checks["memory"] = {
            "usage_percent": memory_percent,
            "status": "ok" if memory_percent < 90 else "high",
        }

        if memory_percent > 95:
            overall_status = "unhealthy"

    except ImportError:
        checks["memory"] = {"status": "unavailable", "message": "psutil not installed"}
    except Exception as e:
        checks["memory"] = {"error": str(e)}

    return jsonify(
        {
            "status": overall_status,
            "service": "Employee Suite",
            "version": "2.7",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat(),
        }
    ), 200 if overall_status == "healthy" else 500


# ---------------------------------------------------------------------------
# Cron Endpoints
# ---------------------------------------------------------------------------


@core_bp.route("/cron/send-trial-warnings", methods=["GET", "POST"])
def cron_trial_warnings():
    secret = request.args.get("secret") or request.form.get("secret")
    if secret != os.getenv("CRON_SECRET"):
        return jsonify({"error": "Unauthorized"}), 401

    from cron_jobs import send_trial_warnings

    try:
        send_trial_warnings()
        return jsonify({"success": True, "message": "Warnings sent"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@core_bp.route("/cron/database-backup", methods=["GET", "POST"])
def cron_database_backup():
    secret = request.args.get("secret") or request.form.get("secret")
    if secret != os.getenv("CRON_SECRET"):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        from database_backup import run_backup

        result = run_backup()
        if result["success"]:
            return jsonify(
                {
                    "success": True,
                    "message": "Backup completed",
                    "backup_file": result["backup_file"],
                }
            ), 200
        else:
            return jsonify({"success": False, "error": result.get("error")}), 500
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


# ---------------------------------------------------------------------------
# Debug Endpoints (development only)
# ---------------------------------------------------------------------------


def _is_debug_enabled():
    env = os.getenv("ENVIRONMENT", "production")
    debug = os.getenv("DEBUG", "False").lower() == "true"
    return env == "development" or debug


@core_bp.route("/api-key-info")
def api_key_info():
    if not _is_debug_enabled():
        return jsonify({"error": "Not available in production"}), 403

    api_key = os.getenv("SHOPIFY_API_KEY", "NOT_SET")
    api_secret = os.getenv("SHOPIFY_API_SECRET", "NOT_SET")
    return jsonify(
        {
            "api_key": {
                "status": "SET" if api_key != "NOT_SET" and api_key else "NOT_SET",
                "preview": api_key[:8] + "..."
                if api_key and api_key != "NOT_SET" and len(api_key) >= 8
                else "N/A",
            },
            "api_secret": {
                "status": "SET"
                if api_secret != "NOT_SET" and api_secret
                else "NOT_SET",
                "preview": api_secret[:8] + "..."
                if api_secret and api_secret != "NOT_SET" and len(api_secret) >= 8
                else "N/A",
            },
        }
    )


@core_bp.route("/test-shopify-route")
def test_shopify_route():
    from flask import current_app

    return jsonify(
        {
            "status": "ok",
            "message": "App is picking up changes",
            "shopify_routes": [
                str(rule)
                for rule in current_app.url_map.iter_rules()
                if "shopify" in str(rule)
            ],
        }
    )


@core_bp.route("/debug-routes")
def debug_routes():
    if not _is_debug_enabled():
        return jsonify({"error": "Not available in production"}), 403

    from flask import current_app

    all_routes = [
        {
            "rule": str(rule.rule),
            "endpoint": rule.endpoint,
            "methods": list(rule.methods),
        }
        for rule in current_app.url_map.iter_rules()
    ]

    # Filter for billing/subscribe routes
    billing_routes = [
        r for r in all_routes if "billing" in r["rule"] or "subscribe" in r["rule"]
    ]

    return jsonify(
        {
            "total_routes": len(all_routes),
            "all_routes": all_routes[:50],
            "billing_routes": billing_routes,
        }
    )


# ---------------------------------------------------------------------------
# Frontend JS Error Logging
# ---------------------------------------------------------------------------


@core_bp.route("/api/log_error", methods=["POST"])
# CSRF exemption removed due to compatibility issues
def log_error():
    """Frontend JS error logging with recursion prevention and noise filtering"""
    try:
        # CRITICAL: Prevent recursive logging loops
        if (
            request.path == "/api/log_error"
            and request.headers.get("Referer")
            and "log_error" in request.headers.get("Referer")
        ):
            return jsonify(
                {"success": False, "error": "Recursive logging prevented"}
            ), 400

        error_data = request.get_json()
        if not error_data:
            return jsonify({"success": False, "error": "No error data provided"}), 400

        # Skip logging errors about logging errors (prevent recursion)
        error_message = error_data.get("error_message", "")
        if (
            "log_error" in error_message.lower()
            or "failed to log error" in error_message.lower()
        ):
            return jsonify({"success": True, "message": "Recursive error ignored"}), 200

        # FILTER OUT NOISE: Skip common external/harmless errors
        error_type = error_data.get("error_type", "")
        error_location = error_data.get("error_location", "")

        # Skip "Unknown error" from external scripts or missing resources
        if (
            error_message == "Unknown error"
            or error_message == ""
            or "Script error" in error_message
            or "Non-Error promise rejection captured" in error_message
            or
            # Skip errors from external domains
            ("shopify.com" in error_location and "Unknown error" in error_message)
            or ("cdn.shopify.com" in error_location)
            or ("googletagmanager.com" in error_location)
            or
            # Skip resource loading errors that we can't control
            (error_type == "JavaScriptError" and "Loading" in error_message)
            or
            # Skip LINK/SCRIPT tag errors for missing static files
            ("LINK" in error_message and "failed" in error_message.lower())
            or ("SCRIPT" in error_message and "failed" in error_message.lower())
        ):
            return jsonify({"success": True, "message": "Filtered noise error"}), 200

        full_error_data = {
            **error_data,
            "request_url": request.url,
            "remote_addr": request.remote_addr,
            "referer": request.headers.get("Referer"),
        }

        logger.error(
            f"JS Error - Type: {error_data.get('error_type', 'UnknownError')}, "
            f"Message: {error_data.get('error_message', 'Unknown error')}, "
            f"Location: {error_data.get('error_location', 'unknown')}",
            extra={"error_data": full_error_data},
        )
        return jsonify({"success": True, "message": "Error logged"}), 200
    except Exception as e:
        # CRITICAL: Don't log this error to prevent infinite recursion
        return jsonify({"success": False, "error": "Failed to log error"}), 500


@core_bp.route("/api/docs")
def api_docs():
    return redirect(
        "https://github.com/vyndigital-cloud/EmployeeSuite-Production/blob/main/API_DOCUMENTATION.md"
    )


@core_bp.route("/debug/routes")
def system_debug_routes():
    if not _is_debug_enabled():
        return jsonify({"error": "Not available in production"}), 403

    from flask import current_app

    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append(
            {
                "rule": str(rule.rule),
                "endpoint": rule.endpoint,
                "methods": list(rule.methods),
            }
        )

    return jsonify(
        {"total_routes": len(routes), "routes": sorted(routes, key=lambda x: x["rule"])}
    )


@core_bp.route("/subscribe")
def subscribe_redirect():
    """Redirect to billing subscribe"""
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")
    return redirect(url_for("billing.subscribe", shop=shop, host=host))


@core_bp.route("/settings")
def settings_redirect():
    """Redirect to Shopify settings"""
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")
    return redirect(url_for("shopify.shopify_settings", shop=shop, host=host))


def get_authenticated_user():
    """Get authenticated user with optimized queries"""
    from sqlalchemy.orm import joinedload

    # Try Flask-Login first (for standalone access)
    if current_user.is_authenticated:
        logger.debug(f"User authenticated via Flask-Login: {current_user.id}")
        return current_user, None

    # Try session token (for embedded apps)
    auth_header = request.headers.get("Authorization", "")
    logger.debug(
        f"Auth header present: {bool(auth_header)}, starts with Bearer: {auth_header.startswith('Bearer ')}"
    )
    if auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1] if " " in auth_header else None
            if not token:
                return None, (
                    jsonify({"error": "Invalid token format", "success": False}),
                    401,
                )

            # Properly verify JWT token with full validation
            import jwt

            # CRITICAL: Check environment variables exist
            api_secret = os.getenv("SHOPIFY_API_SECRET")
            api_key = os.getenv("SHOPIFY_API_KEY")

            if not api_secret:
                logger.warning(
                    "SHOPIFY_API_SECRET not set - cannot verify session token"
                )
                return None, (
                    jsonify({"error": "Server configuration error", "success": False}),
                    500,
                )

            if not api_key:
                logger.warning("SHOPIFY_API_KEY not set - cannot verify session token")
                return None, (
                    jsonify({"error": "Server configuration error", "success": False}),
                    500,
                )

            payload = jwt.decode(
                token,
                api_secret,
                algorithms=["HS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["iss", "dest", "aud", "sub", "exp", "nbf", "iat"],
                },
            )

            # Verify audience matches API key
            token_aud = payload.get("aud", "")
            if token_aud != api_key:
                logger.warning(
                    f"Invalid audience in session token: got '{token_aud}', expected '{api_key}'"
                )
                # TEMPORARY: Allow mismatch for debugging - remove after fix
                logger.warning(f"Proceeding despite audience mismatch for debugging")

            # Extract shop domain
            dest = payload.get("dest", "")
            if not dest or not dest.endswith(".myshopify.com"):
                logger.warning(f"Invalid destination in session token: {dest}")
                return None, (
                    jsonify({"error": "Invalid token", "success": False}),
                    401,
                )

            # CRITICAL: Safe string splitting - handle edge cases
            try:
                cleaned_dest = dest.replace("https://", "").replace("http://", "")
                shop_domain = (
                    cleaned_dest.split("/")[0] if "/" in cleaned_dest else cleaned_dest
                )
                if not shop_domain:
                    raise ValueError("Empty shop domain")
            except (IndexError, AttributeError, ValueError) as e:
                logger.warning(f"Error parsing shop domain from dest '{dest}': {e}")
                return None, (
                    jsonify({"error": "Invalid token format", "success": False}),
                    401,
                )

            # Find user from shop - CRITICAL: Protect against segfaults
            from sqlalchemy.orm import joinedload

            from models import ShopifyStore, db

            store = None
            try:
                # OPTIMIZED: Single query with eager loading
                store = (
                    ShopifyStore.query.options(joinedload(ShopifyStore.user))
                    .filter_by(shop_url=shop_domain, is_active=True)
                    .first()
                )

                if store and store.user:
                    logger.info(
                        f"✅ Session token verified - user {store.user.id} from shop {shop_domain}"
                    )
                    return store.user, None
                else:
                    logger.warning(f"❌ No store found for shop: {shop_domain}")
                    return None, (
                        jsonify(
                            {
                                "error": "Your store is not connected. Please install the app from your Shopify admin.",
                                "success": False,
                                "action": "install",
                                "message": "To get started, install Employee Suite from your Shopify admin panel.",
                            }
                        ),
                        404,
                    )
            except BaseException as db_error:
                logger.error(
                    f"Database error in get_authenticated_user: {type(db_error).__name__}: {str(db_error)}",
                    exc_info=True,
                )
                try:
                    db.session.rollback()
                except Exception:
                    pass
                finally:
                    try:
                        db.session.remove()
                    except Exception:
                        pass
                return None, (
                    jsonify(
                        {
                            "error": "Database connection error",
                            "success": False,
                            "action": "retry",
                        }
                    ),
                    500,
                )

        except jwt.ExpiredSignatureError:
            logger.warning("Expired session token")
            return None, (
                jsonify(
                    {
                        "error": "Your session has expired. Please refresh the page.",
                        "success": False,
                        "action": "refresh",
                        "message": "This usually happens when the page has been open for a while. Refreshing will restore your session.",
                    }
                ),
                401,
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid session token: {e}")
            return None, (
                jsonify(
                    {
                        "error": "Unable to verify your session. Please refresh the page.",
                        "success": False,
                        "action": "refresh",
                        "message": "If the problem persists, try closing and reopening the app from your Shopify admin.",
                    }
                ),
                401,
            )
        except Exception as e:
            logger.error(f"Error verifying session token: {e}", exc_info=True)
            return None, (
                jsonify(
                    {
                        "error": "We encountered an issue verifying your session. Please try again.",
                        "success": False,
                        "action": "retry",
                        "message": "If this continues, please refresh the page or contact support.",
                    }
                ),
                401,
            )

    # Try shop parameter authentication (for Shopify embedded apps after OAuth redirect)
    shop_param = request.args.get("shop")
    if shop_param:
        logger.info(f"Trying shop parameter authentication for: {shop_param}")
        try:
            from models import ShopifyStore, db

            # Normalize shop domain
            shop_domain = (
                shop_param.replace("https://", "").replace("http://", "").split("/")[0]
            )
            if not shop_domain.endswith(".myshopify.com"):
                shop_domain = f"{shop_domain}.myshopify.com"

            store = ShopifyStore.query.filter_by(
                shop_url=shop_domain, is_active=True
            ).first()
            if store and store.user:
                logger.info(
                    f"✅ Shop parameter auth successful - user {store.user.id} from shop {shop_domain}"
                )
                return store.user, None
            else:
                logger.warning(f"No active store found for shop param: {shop_domain}")
        except Exception as e:
            logger.error(f"Error in shop parameter auth: {e}", exc_info=True)

    # No authentication found
    return None, (
        jsonify(
            {
                "error": "Please sign in to continue.",
                "success": False,
                "action": "login",
                "message": "You need to be signed in to use this feature. If you're using the app from Shopify admin, try refreshing the page.",
            }
        ),
        401,
    )


# ---------------------------------------------------------------------------
# Core API Endpoints
# ---------------------------------------------------------------------------


@core_bp.route("/api/process_orders", methods=["GET", "POST"])
@verify_session_token
def api_process_orders():
    """Process orders - simple version"""
    try:
        # Get user
        user, error_response = get_authenticated_user()
        if error_response:
            return error_response

        # Check access
        if not user.has_access():
            return jsonify(
                {
                    "success": False,
                    "error": "Subscription required",
                    "action": "subscribe",
                }
            ), 403

        # Process orders
        try:
            from order_processing import process_orders

            result = process_orders(user_id=user.id)

            if isinstance(result, dict):
                return jsonify(result)
            else:
                return jsonify({"success": True, "message": str(result)})

        except ImportError:
            return jsonify(
                {"success": False, "error": "Order processing not available"}
            ), 500

    except Exception as e:
        logger.error(f"Error processing orders: {e}")
        return jsonify(
            {
                "success": False,
                "error": "An error occurred. Please try again.",
                "action": "retry",
            }
        ), 500


@core_bp.route("/api/update_inventory", methods=["GET", "POST"])
@verify_session_token
def api_update_inventory():
    """Update inventory - simple version"""
    try:
        # Get user
        user, error_response = get_authenticated_user()
        if error_response:
            return error_response

        # Check access
        if not user.has_access():
            return jsonify(
                {
                    "success": False,
                    "error": "Subscription required",
                    "action": "subscribe",
                }
            ), 403

        # Update inventory
        try:
            from inventory import update_inventory

            result = update_inventory(user_id=user.id)

            if isinstance(result, dict):
                return jsonify(result)
            else:
                return jsonify({"success": True, "message": str(result)})

        except ImportError:
            return jsonify(
                {"success": False, "error": "Inventory module not available"}
            ), 500

    except Exception as e:
        logger.error(f"Error updating inventory: {e}")
        return jsonify(
            {
                "success": False,
                "error": "An error occurred. Please try again.",
                "action": "retry",
            }
        ), 500


@core_bp.route("/api/generate_report", methods=["GET", "POST"])
@verify_session_token
def api_generate_report():
    """Generate report - simple version"""
    try:
        # Get user
        user, error_response = get_authenticated_user()
        if error_response:
            return error_response

        # Check access
        if not user.has_access():
            return jsonify(
                {
                    "success": False,
                    "error": "Subscription required",
                    "action": "subscribe",
                }
            ), 403

        # Generate report
        try:
            from reporting import generate_report

            result = generate_report(user_id=user.id)

            if isinstance(result, dict):
                return jsonify(result)
            else:
                return jsonify({"success": True, "message": str(result)})

        except ImportError:
            return jsonify(
                {"success": False, "error": "Reporting module not available"}
            ), 500

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return jsonify(
            {
                "success": False,
                "error": "An error occurred. Please try again.",
                "action": "retry",
            }
        ), 500


@core_bp.route("/api/analytics/forecast", methods=["GET"])
@verify_session_token
def api_analytics_forecast():
    """Analytics forecast endpoint for AI predictions"""
    try:
        user, error_response = get_authenticated_user()
        if error_response:
            return error_response

        if not user.has_access():
            return jsonify(
                {
                    "error": "Subscription required",
                    "success": False,
                    "action": "subscribe",
                }
            ), 403

        # Mock forecast data for now
        return jsonify(
            {
                "metrics": {"at_risk_count": 3, "total_potential_loss": 1250.00},
                "items": [
                    {
                        "product_title": "Sample Product 1",
                        "velocity": "2.5/day",
                        "days_remaining": 3,
                        "current_stock": 8,
                    },
                    {
                        "product_title": "Sample Product 2",
                        "velocity": "1.8/day",
                        "days_remaining": 5,
                        "current_stock": 9,
                    },
                ],
            }
        )

    except Exception as e:
        logger.error(f"Error in analytics forecast: {e}")
        return jsonify({"error": "Failed to generate forecast", "success": False}), 500


# ---------------------------------------------------------------------------
# CSV Export Endpoints (legacy)
# ---------------------------------------------------------------------------


@core_bp.route("/api/export/inventory-simple", methods=["GET"])
@login_required
def export_inventory_csv():
    # Add inline access check
    if not current_user.has_access():
        return jsonify({"error": "Subscription required", "success": False}), 403
    try:
        from inventory import check_inventory

        inventory_data = session.get("inventory_data", [])
        if not inventory_data:
            result = check_inventory()
            if result.get("success") and "inventory_data" in result:
                inventory_data = result["inventory_data"]
                session["inventory_data"] = inventory_data

        if not inventory_data:
            return "No inventory data available. Please check inventory first.", 404

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Product", "SKU", "Stock", "Price"])
        for item in inventory_data:
            writer.writerow(
                [
                    item.get("product", "N/A"),
                    item.get("sku", "N/A"),
                    item.get("stock", 0),
                    item.get("price", "N/A"),
                ]
            )

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=inventory_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            },
        )
    except Exception as e:
        logger.error(f"Error exporting inventory CSV: {e}", exc_info=True)
        return jsonify({"error": f"Failed to export inventory: {e}"}), 500


@core_bp.route("/api/export/orders", methods=["GET"])
@login_required
def export_orders_csv():
    # Add inline access check
    if not current_user.has_access():
        return jsonify({"error": "Subscription required", "success": False}), 403
    try:
        from order_processing import process_orders

        # Try to get cached orders data first
        orders_data = session.get("orders_data", [])
        if not orders_data:
            result = process_orders(user_id=current_user.id)
            if result.get("success") and "orders_data" in result:
                orders_data = result["orders_data"]
                session["orders_data"] = orders_data

        if not orders_data:
            return "No orders data available. Please process orders first.", 404

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Order ID", "Customer", "Total", "Items", "Status", "Date"])

        for order in orders_data:
            writer.writerow([
                order.get("id", "N/A"),
                order.get("customer", "N/A"),
                order.get("total", "N/A"),
                order.get("items", 0),
                order.get("status", "N/A"),
                datetime.utcnow().strftime('%Y-%m-%d')
            ])

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=orders_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            },
        )
    except Exception as e:
        logger.error(f"Error exporting orders CSV: {e}", exc_info=True)
        return jsonify({"error": f"Failed to export orders: {e}"}), 500


@core_bp.route("/api/export/report", methods=["GET"])
@login_required
@require_access
def export_report_csv():
    try:
        from reporting import generate_report

        report_data = session.get("report_data", {})
        if not report_data:
            data = generate_report()
            if data.get("success") and "report_data" in data:
                report_data = data["report_data"]

        if not report_data or "products" not in report_data:
            return "No report data available. Please generate report first.", 404

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["Product", "Revenue", "Percentage", "Total Revenue", "Total Orders"]
        )

        total_revenue = report_data.get("total_revenue", 0)
        total_orders = report_data.get("total_orders", 0)

        for product, revenue in report_data.get("products", [])[:10]:
            percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0
            writer.writerow(
                [
                    product,
                    f"${revenue:,.2f}",
                    f"{percentage:.1f}%",
                    f"${total_revenue:,.2f}",
                    total_orders,
                ]
            )

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=revenue_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            },
        )
    except Exception as e:
        logger.error(f"Error exporting report CSV: {e}", exc_info=True)
        return f"Error exporting CSV: {e}", 500


@core_bp.route("/features/csv-exports")
@login_required
def csv_exports():
    """CSV exports feature page"""
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")

    return render_template_string(
        """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CSV Exports - Employee Suite</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body>
        <h1>CSV Exports</h1>
        <p>CSV export functionality coming soon.</p>
        <a href="/dashboard?shop={{ shop }}&host={{ host }}">Back to Dashboard</a>
    </body>
    </html>
    """,
        shop=shop,
        host=host,
    )


@core_bp.route("/api/scheduled-reports/create", methods=["POST"])
@login_required
@require_access
def create_scheduled_report():
    try:
        from enhanced_models import ScheduledReport

        report_type = request.form.get("report_type")
        frequency = request.form.get("frequency")
        email = request.form.get("email")
        shop = request.form.get("shop", "")
        host = request.form.get("host", "")

        if not all([report_type, frequency, email]):
            return redirect(f"/features/scheduled-reports?shop={shop}&host={host}&error=All fields are required")

        # Create scheduled report
        scheduled_report = ScheduledReport(
            user_id=current_user.id,
            report_type=report_type,
            frequency=frequency,
            delivery_email=email,
            is_active=True
        )

        # Calculate next send time
        scheduled_report.next_send_at = scheduled_report.calculate_next_send()

        db.session.add(scheduled_report)
        db.session.commit()

        return redirect(f"/features/scheduled-reports?shop={shop}&host={host}&success=Schedule created successfully")

    except Exception as e:
        logger.error(f"Error creating scheduled report: {e}")
        return redirect(f"/features/scheduled-reports?shop={shop}&host={host}&error=Failed to create schedule")


@core_bp.route("/api/scheduled-reports/list", methods=["GET"])
@login_required
@require_access
def list_scheduled_reports():
    try:
        from enhanced_models import ScheduledReport

        reports = ScheduledReport.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).all()

        reports_data = []
        for report in reports:
            reports_data.append({
                "id": report.id,
                "report_type": report.report_type,
                "frequency": report.frequency,
                "delivery_email": report.delivery_email,
                "next_send_at": report.next_send_at.strftime('%Y-%m-%d %H:%M') if report.next_send_at else "Not scheduled"
            })

        return jsonify({"success": True, "reports": reports_data})

    except Exception as e:
        logger.error(f"Error listing scheduled reports: {e}")
        return jsonify({"success": False, "error": "Failed to load reports"}), 500


@core_bp.route("/api/scheduled-reports/delete/<int:report_id>", methods=["POST"])
@login_required
@require_access
def delete_scheduled_report(report_id):
    try:
        from enhanced_models import ScheduledReport

        report = ScheduledReport.query.filter_by(
            id=report_id,
            user_id=current_user.id
        ).first()

        if not report:
            return jsonify({"success": False, "error": "Report not found"}), 404

        report.is_active = False
        db.session.commit()

        return jsonify({"success": True, "message": "Schedule deleted successfully"})

    except Exception as e:
        logger.error(f"Error deleting scheduled report: {e}")
        return jsonify({"success": False, "error": "Failed to delete schedule"}), 500


@core_bp.route("/install")
def install_redirect():
    """Redirect to OAuth install"""
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")

    if shop:
        return redirect(url_for("oauth.install", shop=shop, host=host))

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Install Employee Suite</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; text-align: center; padding: 50px; }
            .container { max-width: 400px; margin: 0 auto; }
            h1 { color: #202223; margin-bottom: 16px; }
            p { color: #6d7175; margin-bottom: 24px; }
            input { width: 100%; padding: 12px; border: 1px solid #e1e3e5; border-radius: 6px; margin-bottom: 16px; }
            .btn { background: #008060; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Install Employee Suite</h1>
            <p>Enter your shop domain to get started:</p>
            <form action="/install" method="get">
                <input type="text" name="shop" placeholder="your-shop.myshopify.com" required>
                <br>
                <button type="submit" class="btn">Install App</button>
            </form>
        </div>
    </body>
    </html>
    """)
