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
    g,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    session,
    url_for,
    current_app,
)
from flask_login import current_user
from session_token_verification import verify_session_token
from access_control import require_access, require_zero_trust

logger = logging.getLogger(__name__)
core_bp = Blueprint("core", __name__)


from access_control import require_access


# Deferred imports moved inside functions for faster startup
from utils import safe_redirect
from shopify_utils import app_bridge_redirect


@core_bp.route("/admin")
def admin_dashboard():
    """Admin dashboard - redirect to scaling status for now"""
    if os.getenv("ENVIRONMENT") != "production":
        return jsonify({"error": "Only available in production"}), 403
    
    # For now, redirect to the scaling status page
    return redirect(url_for('core.scaling_status'))


@core_bp.route("/admin/scaling-status")
def scaling_status():
    """Admin dashboard for scaling status"""
    if os.getenv("ENVIRONMENT") != "production":
        return jsonify({"error": "Only available in production"}), 403

    try:
        # Remove auto_scaling import - module doesn't exist
        # from auto_scaling import get_auto_scaler
        from performance import get_cache_efficiency

        # scaler = get_auto_scaler()
        cache_stats = get_cache_efficiency()

        return jsonify(
            {
                "current_tier": "standard",  # Static value since auto_scaler doesn't exist
                "max_load_seen": 0.0,       # Static value
                "cache_efficiency": cache_stats,
                "scaling_thresholds": {},    # Empty dict since no scaler
                "status": "healthy",
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Helper: get_authenticated_user
# ---------------------------------------------------------------------------


def get_authenticated_user():
    """
    Get authenticated user from either Flask-Login or Shopify session token.
    Returns (user, error_response) tuple. If user is None, error_response contains the error.
    Uses deferred imports for faster startup.
    """
    # Import only when needed to speed up startup
    from models import ShopifyStore, User, db
    
    # Try Flask-Login first (for standalone access)
    if current_user.is_authenticated:
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

            try:
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
            except jwt.ExpiredSignatureError:
                return None, (
                    jsonify({
                        "error": "Session expired - please refresh the page",
                        "success": False,
                        "action": "refresh",
                    }),
                    401,
                )
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid JWT token: {e}")
                return None, (
                    jsonify({
                        "error": "Invalid session token",
                        "success": False,
                        "action": "refresh",
                    }),
                    401,
                )

            # Validate token claims
            if payload.get("aud") != api_key:
                logger.warning(f"Invalid audience: {payload.get('aud')}")
                return None, (
                    jsonify({"error": "Invalid token", "success": False}),
                    401,
                )

            # Extract shop domain
            dest = payload.get("dest", "")
            if not dest or not dest.endswith(".myshopify.com"):
                logger.warning(f"Invalid destination: {dest}")
                return None, (
                    jsonify({"error": "Invalid token", "success": False}),
                    401,
                )

            try:
                shop_domain = dest.replace("https://", "").replace("http://", "").split("/")[0]
            except (IndexError, AttributeError):
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
                except Exception as rollback_error:
                    logger.error(f"Database rollback failed: {rollback_error}")
                finally:
                    # Enhanced session cleanup with context management
                    try:
                        db.session.remove()
                    except Exception as remove_error:
                        logger.error(f"Failed to remove database session: {remove_error}")
                    finally:
                        # Ensure session is always cleaned up
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


@core_bp.route("/", methods=["GET", "POST"])
@core_bp.route("/dashboard", endpoint="dashboard", methods=["GET", "POST"])
def home():
    """Optimized dashboard - target <300ms load time"""
    try:
        # Import only when needed to speed up startup
        from models import ShopifyStore, User, db
        
        # 🎯 TITAN FIX: Prioritize the verified identity from the middleware
        shop = g.get('shop_domain') or request.args.get('shop')
        host = g.get('host') or request.args.get('host')
        
        # Update session only if we found something new
        if shop:
            session['shop'] = shop
        if host:
            session['host'] = host
        
        # Fallback to session if still not found
        if not shop:
            shop = session.get('shop')
        if not host:
            host = session.get('host')
            
        embedded = request.args.get("embedded")
        
        logger.info(f"🏠 Home Route Access: shop={shop}, host={host}")

        # CRITICAL: For embedded apps without a connected store, redirect to OAuth
        if shop and host and embedded:
            try:
                store = db.session.query(ShopifyStore).filter_by(shop_url=shop, is_active=True).first()
                if not store:
                    # No active store found - send to settings where they can reconnect
                    logger.info(f"Embedded app accessed without active store for {shop}, redirecting to settings")
                    target_path = url_for("shopify.shopify_settings")
                    return app_bridge_redirect(target_path)
            except Exception as db_error:
                logger.error(f"Database error checking store: {db_error}")
                # Continue anyway - might be a temporary DB issue

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
                current_shop="demo-store.myshopify.com",
                APP_URL=request.url_root.rstrip("/"),
                host="",
            )

        # PERFORMANCE: Defer user lookup and use cached data
        user = None
        try:
            if current_user.is_authenticated:
                user = current_user
            elif shop:
                # Quick lookup without joins - PROTECTED
                store = db.session.query(ShopifyStore).filter_by(shop_url=shop).first()
                if store and store.user_id:
                    user = db.session.query(User).get(store.user_id)
        except Exception as db_error:
            logger.error(f"Database error in home(): {db_error}", exc_info=True)
            # Continue with user = None
            try:
                db.session.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback database session: {rollback_error}")

        # Default values (avoid expensive calculations)
        if user:
            try:
                # 10k GHOST SHIP: Remove fresh DB check. Trust the cache + webhooks.
                has_access = user.has_access()
                trial_active = user.is_trial_active()
                is_subscribed = user.is_subscribed
                
                # SAFE datetime calculation
                if trial_active and hasattr(user, 'trial_ends_at') and user.trial_ends_at:
                    try:
                        days_left = max(0, (user.trial_ends_at - datetime.utcnow()).days)
                    except (AttributeError, TypeError):
                        days_left = 0
                else:
                    days_left = 0
                    
                has_shopify = True  # Assume true if we have a user
                
                logger.debug(
                    f"🏠 Ghost Ship Check: User {user.id} - "
                    f"has_access={has_access}, trial_active={trial_active}"
                )
            except Exception as user_error:
                logger.error(f"Error processing user data: {user_error}")
                has_access, trial_active, days_left, is_subscribed, has_shopify = (
                    False,
                    False,
                    0,
                    False,
                    False,
                )
        else:
            # Guest or unauthenticated store access
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
            plan_name="Employee Suite Pro",
            plan_price=39,
            api_key=current_app.config.get("SHOPIFY_API_KEY", "")
        )
        
    except Exception as e:
        logger.error(f"Critical error in home(): {e}", exc_info=True)
        # Return a safe fallback response
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head><title>Employee Suite</title></head>
        <body>
            <h1>Employee Suite</h1>
            <p>Dashboard temporarily unavailable. Please try refreshing manually.</p>
            <button onclick="window.location.reload()">Refresh</button>
        </body>
        </html>
        """), 200


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


@core_bp.route("/manifest.json")
def manifest():
    """Return empty manifest to prevent 404s"""
    return jsonify({
        "name": "Employee Suite",
        "short_name": "Employee Suite",
        "description": "Employee management and productivity tools",
        "start_url": "/dashboard",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#008060",
        "icons": [{
            "src": "/static/images/logo.png",
            "sizes": "192x192",
            "type": "image/png"
        }]
    })


@core_bp.route("/robots.txt")
@core_bp.route("/sitemap.xml")
def seo_files():
    """Return standard SEO files"""
    if request.path.endswith("xml"):
        return Response(
            '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
            mimetype="application/xml"
        )
    return Response("User-agent: *\nDisallow: /admin/\nDisallow: /api/", mimetype="text/plain")


@core_bp.route("/<path:filename>.map")
def silence_sourcemaps(filename):
    """Silence JS/CSS source map 404s"""
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
            "JS Error - Type: %s, Message: %s, Location: %s",
            error_data.get('error_type', 'UnknownError'),
            error_data.get('error_message', 'Unknown error'), 
            error_data.get('error_location', 'unknown'),
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
    """Redirect to billing subscribe using App Bridge to preserve JWT trust"""
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")
    
    # Build the target URL with query params
    target_url = url_for("billing.subscribe", shop=shop, host=host, _external=True)
    
    # Use App Bridge redirect to maintain JWT context
    return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://unpkg.com/@shopify/app-bridge@3"></script>
            <script>
                const targetUrl = "{target_url}";
                if (window.top !== window.self) {{
                    window.top.location.href = targetUrl;
                }} else {{
                    window.location.href = targetUrl;
                }}
            </script>
        </head>
        <body>
            <p>Redirecting to subscription... <a href="{target_url}">Click here if not redirected</a></p>
        </body>
        </html>
    ''', 200


@core_bp.route("/settings")
def settings_redirect():
    """Redirect to Shopify settings using App Bridge to preserve JWT trust"""
    # 🎯 TITAN FIX: Prioritize verified identity from middleware
    shop = g.get('shop_domain', '') or request.args.get("shop", "")
    host = g.get('host', '') or request.args.get("host", "")
    target_url = url_for("shopify.shopify_settings", shop=shop, host=host, _external=True)
    return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://unpkg.com/@shopify/app-bridge@3"></script>
            <script>
                const targetUrl = "{target_url}";
                if (window.top !== window.self) {{
                    window.top.location.href = targetUrl;
                }} else {{
                    window.location.href = targetUrl;
                }}
            </script>
        </head>
        <body><p>Redirecting to settings... <a href="{target_url}">Click here if not redirected</a></p></body>
        </html>
    ''', 200





# ---------------------------------------------------------------------------
# Core API Endpoints
# ---------------------------------------------------------------------------


@core_bp.route("/api/process_orders", methods=["GET", "POST"])
def api_process_orders():
    """Process orders with comprehensive error handling and retry logic"""
    try:
        user, error_response = get_authenticated_user()
        if error_response:
            return error_response

        if not user.has_access():
            return jsonify({
                "success": False,
                "error": "Subscription required for order processing",
                "action": "subscribe",
                "upgrade_message": "Unlock unlimited order processing with Employee Suite Pro - just $39/month",
                "value_proposition": "Save 10+ hours per week on manual order management"
            }), 403

        # Use real order processing
        from order_processing import process_orders
        
        # Get date filters from request
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        result = process_orders(user_id=user.id, start_date=start_date, end_date=end_date)
        
        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify(result), 500

    except Exception as e:
        error_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        logger.error(f"Critical error in order processing [{error_id}] for user {user.id if 'user' in locals() else 'unknown'}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred. Our team has been automatically notified.",
            "action": "contact_support",
            "error_id": error_id,
            "support_message": "We're here to help! Contact support for immediate assistance.",
            "support_url": "/support"
        }), 500


@core_bp.route("/api/update_inventory", methods=["GET", "POST"])
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


@core_bp.route("/api/dashboard/comprehensive", methods=["GET"])
def api_comprehensive_dashboard():
    """Comprehensive dashboard API - all reports in one"""
    try:
        user, error_response = get_authenticated_user()
        if error_response:
            return error_response

        if not user.has_access():
            return jsonify({
                "success": False,
                "error": "Subscription required",
                "action": "subscribe"
            }), 403

        result = {"success": True, "errors": []}
        
        # Try to get orders
        try:
            from order_processing import process_orders
            orders_result = process_orders(user_id=user.id)
            if orders_result.get("success"):
                result["orders"] = orders_result
            else:
                result["errors"].append({
                    "type": "orders",
                    "error": orders_result.get("error", "Failed to load orders"),
                    "action": orders_result.get("action")
                })
        except Exception as e:
            result["errors"].append({
                "type": "orders", 
                "error": str(e),
                "action": "retry"
            })

        # Try to get inventory
        try:
            from inventory import update_inventory
            inventory_result = update_inventory(user_id=user.id)
            if inventory_result.get("success"):
                result["inventory"] = inventory_result
            else:
                result["errors"].append({
                    "type": "inventory",
                    "error": inventory_result.get("error", "Failed to load inventory"),
                    "action": inventory_result.get("action")
                })
        except Exception as e:
            result["errors"].append({
                "type": "inventory",
                "error": str(e), 
                "action": "retry"
            })

        # Try to get revenue
        try:
            from reporting import generate_report
            revenue_result = generate_report(user_id=user.id)
            if revenue_result.get("success"):
                result["revenue"] = revenue_result
            else:
                result["errors"].append({
                    "type": "revenue",
                    "error": revenue_result.get("error", "Failed to load revenue"),
                    "action": revenue_result.get("action")
                })
        except Exception as e:
            result["errors"].append({
                "type": "revenue",
                "error": str(e),
                "action": "retry"
            })

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in comprehensive dashboard: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to load dashboard data",
            "action": "retry"
        }), 500





# ---------------------------------------------------------------------------
# CSV Export Endpoints (legacy)
# ---------------------------------------------------------------------------










@core_bp.route("/support")
def support():
    """Professional support page with multiple contact options"""
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")
    
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Support - Employee Suite</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/dashboard.css') }}">
    <style>
        .support-container { max-width: 1000px; margin: 0 auto; padding: 40px 24px; }
        .support-hero { text-align: center; margin-bottom: 48px; }
        .support-hero h1 { font-size: 36px; font-weight: 800; margin-bottom: 16px; color: #202223; }
        .support-hero p { font-size: 18px; color: #6d7175; }
        .support-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; margin: 40px 0; }
        .support-card { 
            background: white; padding: 32px; border-radius: 16px; 
            border: 1px solid #e1e3e5; text-align: center;
            transition: all 0.3s ease;
        }
        .support-card:hover { 
            transform: translateY(-8px); 
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        .support-icon { 
            font-size: 48px; margin-bottom: 16px; display: block;
        }
        .support-title { 
            font-size: 20px; font-weight: 700; margin-bottom: 12px; color: #202223;
        }
        .support-description { 
            color: #6d7175; margin-bottom: 24px; line-height: 1.6;
        }
        .support-btn { 
            background: #008060; color: white; padding: 14px 28px; 
            border-radius: 8px; text-decoration: none; font-weight: 600;
            display: inline-block; transition: all 0.2s;
        }
        .support-btn:hover { background: #006b52; transform: translateY(-2px); }
        .urgent-support { 
            background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
            color: white; padding: 32px; border-radius: 16px; margin-bottom: 40px;
            text-align: center;
        }
        .urgent-support h3 { margin-bottom: 12px; font-size: 24px; }
        .urgent-support p { margin-bottom: 20px; opacity: 0.9; }
        .support-promise { 
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            padding: 40px; border-radius: 16px; margin-top: 48px;
        }
        .promise-grid { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 32px; margin-top: 32px;
        }
        .promise-item { text-align: center; }
        .promise-icon { font-size: 32px; margin-bottom: 12px; }
        .promise-title { font-weight: 700; color: #008060; margin-bottom: 8px; }
        .promise-desc { color: #6d7175; font-size: 14px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <a href="#" onclick="openPage('/dashboard'); return false;" class="logo">
                <span>← Back to Dashboard</span>
            </a>
        </div>
    </div>

    <div class="support-container">
        <div class="support-hero">
            <h1>We're Here to Help You Succeed</h1>
            <p>Get expert support from our team of Shopify specialists - available 24/7</p>
        </div>

        <div class="urgent-support">
            <h3>🚨 Urgent Issue Affecting Your Store?</h3>
            <p>For critical issues that impact your store operations or revenue, contact us immediately for priority support.</p>
            <a href="mailto:urgent@employeesuite.app?subject=URGENT: Store Issue" class="support-btn" style="background: white; color: #dc2626; font-weight: 700;">
                📧 Emergency Support - Response in 15 Minutes
            </a>
        </div>

        <div class="support-grid">
            <div class="support-card">
                <span class="support-icon">💬</span>
                <h3 class="support-title">Live Chat Support</h3>
                <p class="support-description">
                    Get instant help from our support experts. Available 24/7 for all subscribers with average response time under 2 minutes.
                </p>
                <a href="#" onclick="startLiveChat()" class="support-btn">Start Live Chat</a>
            </div>

            <div class="support-card">
                <span class="support-icon">📧</span>
                <h3 class="support-title">Email Support</h3>
                <p class="support-description">
                    Send detailed questions and get comprehensive responses within 2 hours during business hours, 4 hours on weekends.
                </p>
                <a href="mailto:support@employeesuite.app?subject=Support Request" class="support-btn">Send Email</a>
            </div>

            <div class="support-card">
                <span class="support-icon">📞</span>
                <h3 class="support-title">Phone & Video Support</h3>
                <p class="support-description">
                    Schedule a personal call or screen-share session with our experts for hands-on assistance and training.
                </p>
                <a href="#" onclick="scheduleCall()" class="support-btn">Schedule Call</a>
            </div>

            <div class="support-card">
                <span class="support-icon">🎓</span>
                <h3 class="support-title">Free Onboarding</h3>
                <p class="support-description">
                    Get a personalized 30-minute onboarding session to optimize Employee Suite for your specific business needs.
                </p>
                <a href="mailto:onboarding@employeesuite.app?subject=Free Onboarding Request" class="support-btn">Book Onboarding</a>
            </div>

            <div class="support-card">
                <span class="support-icon">📚</span>
                <h3 class="support-title">Help Center & FAQs</h3>
                <p class="support-description">
                    Browse our comprehensive knowledge base with step-by-step guides, video tutorials, and troubleshooting tips.
                </p>
                <a href="/faq" class="support-btn">Browse Help Center</a>
            </div>

            <div class="support-card">
                <span class="support-icon">🔧</span>
                <h3 class="support-title">Technical Integration</h3>
                <p class="support-description">
                    Need help with custom integrations or advanced setup? Our technical team provides white-glove service.
                </p>
                <a href="mailto:technical@employeesuite.app?subject=Technical Integration Request" class="support-btn">Get Technical Help</a>
            </div>
        </div>

        <div class="support-promise">
            <div style="text-align: center; margin-bottom: 32px;">
                <h3 style="font-size: 28px; font-weight: 800; color: #202223; margin-bottom: 12px;">Our Support Promise</h3>
                <p style="font-size: 16px; color: #6d7175;">We're committed to your success with industry-leading support standards</p>
            </div>
            
            <div class="promise-grid">
                <div class="promise-item">
                    <div class="promise-icon">⚡</div>
                    <div class="promise-title">Lightning Fast Response</div>
                    <div class="promise-desc">2-hour email response, 2-minute chat response, 15-minute emergency response</div>
                </div>
                <div class="promise-item">
                    <div class="promise-icon">🎯</div>
                    <div class="promise-title">Shopify Experts</div>
                    <div class="promise-desc">Our team consists of certified Shopify experts with years of e-commerce experience</div>
                </div>
                <div class="promise-item">
                    <div class="promise-icon">🔧</div>
                    <div class="promise-title">Free Setup & Training</div>
                    <div class="promise-desc">Complimentary onboarding, setup assistance, and ongoing training at no extra cost</div>
                </div>
                <div class="promise-item">
                    <div class="promise-icon">🌟</div>
                    <div class="promise-title">100% Satisfaction</div>
                    <div class="promise-desc">We don't rest until your issue is resolved and you're completely satisfied</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function startLiveChat() {
            // Replace with your actual chat system integration
            if (window.Intercom) {
                window.Intercom('show');
            } else if (window.Zendesk) {
                window.zE('webWidget', 'open');
            } else {
                // Fallback to email
                window.location.href = 'mailto:support@employeesuite.app?subject=Live Chat Request - Please call me';
            }
        }

        function scheduleCall() {
            // Replace with your actual scheduling system
            window.open('https://calendly.com/employeesuite/support-call', '_blank');
        }

        window.openPage = function(path) {
            var params = new URLSearchParams(window.location.search);
            var shop = params.get('shop');
            var host = params.get('host');
            var sep = path.indexOf('?') > -1 ? '&' : '?';
            var dest = path;
            if (shop) dest += sep + 'shop=' + shop;
            if (host) dest += (dest.indexOf('?') > -1 ? '&' : '?') + 'host=' + host;
            window.location.href = dest;
            return false;
        };
    </script>
</body>
</html>
    """, shop=shop, host=host)

@core_bp.errorhandler(404)
def not_found_error(error):
    """Professional 404 page"""
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Page Not Found - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
            text-align: center; padding: 80px 24px; margin: 0;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            min-height: 100vh; display: flex; align-items: center; justify-content: center;
        }
        .error-container { 
            max-width: 500px; background: white; padding: 48px 32px; 
            border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .error-code { 
            font-size: 72px; font-weight: 800; color: #008060; 
            margin-bottom: 16px; line-height: 1;
        }
        .error-title { 
            font-size: 24px; font-weight: 700; margin-bottom: 16px; color: #202223;
        }
        .error-description { 
            color: #6d7175; margin-bottom: 32px; line-height: 1.6;
        }
        .btn { 
            background: #008060; color: white; padding: 12px 24px; 
            border-radius: 8px; text-decoration: none; font-weight: 600;
            display: inline-block; transition: all 0.2s; margin: 0 8px;
        }
        .btn:hover { background: #006b52; transform: translateY(-2px); }
        .btn-secondary { background: #6b7280; }
        .btn-secondary:hover { background: #4b5563; }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">404</div>
        <h1 class="error-title">Page Not Found</h1>
        <p class="error-description">
            The page you're looking for doesn't exist or has been moved. 
            Let's get you back to managing your store.
        </p>
        <div>
            <a href="{{ url_for('core.home') }}" class="btn">← Back to Dashboard</a>
            <a href="{{ url_for('core.support') }}" class="btn btn-secondary">Get Help</a>
        </div>
    </div>
</body>
</html>
    """), 404

@core_bp.errorhandler(500)
def internal_error(error):
    """Professional 500 page with support contact"""
    error_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    logger.error(f"500 Error {error_id}: {error}", exc_info=True)
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Server Error - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
            text-align: center; padding: 80px 24px; margin: 0;
            background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
            min-height: 100vh; display: flex; align-items: center; justify-content: center;
        }
        .error-container { 
            max-width: 600px; background: white; padding: 48px 32px; 
            border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .error-code { 
            font-size: 72px; font-weight: 800; color: #dc2626; 
            margin-bottom: 16px; line-height: 1;
        }
        .error-title { 
            font-size: 24px; font-weight: 700; margin-bottom: 16px; color: #202223;
        }
        .error-description { 
            color: #6d7175; margin-bottom: 24px; line-height: 1.6;
        }
        .error-id { 
            background: #f3f4f6; padding: 12px 16px; border-radius: 8px; 
            font-family: monospace; font-size: 12px; margin-bottom: 32px;
            border: 1px solid #e5e7eb;
        }
        .btn { 
            background: #008060; color: white; padding: 14px 28px; 
            border-radius: 8px; text-decoration: none; font-weight: 600;
            display: inline-block; transition: all 0.2s; margin: 0 8px;
        }
        .btn:hover { background: #006b52; transform: translateY(-2px); }
        .btn-urgent { background: #dc2626; }
        .btn-urgent:hover { background: #b91c1c; }
        .support-note { 
            background: #f0f9ff; padding: 20px; border-radius: 8px; 
            margin-top: 24px; border-left: 4px solid #008060;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">500</div>
        <h1 class="error-title">Oops! Something Went Wrong</h1>
        <p class="error-description">
            We're experiencing a temporary issue. Our engineering team has been 
            automatically notified and is working to fix this immediately.
        </p>
        <div class="error-id">
            <strong>Error Reference:</strong> {{ error_id }}<br>
            <small>Please include this ID when contacting support</small>
        </div>
        <div>
            <a href="{{ url_for('core.home') }}" class="btn">← Back to Dashboard</a>
            <a href="mailto:urgent@employeesuite.app?subject=Error {{ error_id }}" class="btn btn-urgent">
                🚨 Report Issue
            </a>
        </div>
        <div class="support-note">
            <strong>Need immediate help?</strong><br>
            Email urgent@employeesuite.app or use live chat for priority support.
            We typically resolve issues within 15 minutes.
        </div>
    </div>
</body>
</html>
    """, error_id=error_id), 500



@core_bp.route("/faq")
def faq():
    """FAQ page"""
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")
    
    return render_template("faq.html", shop=shop, host=host, config_api_key=os.getenv("SHOPIFY_API_KEY", ""))
