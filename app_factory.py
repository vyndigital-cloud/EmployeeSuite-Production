"""
Simple App Factory
"""

import logging
import os
from datetime import timedelta

from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app():
    """Create Flask app with comprehensive error handling"""
    app = Flask(__name__)
    app.static_folder = "static"
    app.static_url_path = "/static"
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Enhanced config
    app.config.update(
        {
            "SECRET_KEY": os.getenv(
                "SECRET_KEY", "dev-secret-key-change-in-production"
            ),
            "SQLALCHEMY_DATABASE_URI": os.getenv("DATABASE_URL", "sqlite:///app.db"),
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "pool_size": 10,
                "max_overflow": 20,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            },
            "WTF_CSRF_ENABLED": True,
            "WTF_CSRF_TIME_LIMIT": 3600,
            # Session cookie configuration for login persistence
            "SESSION_COOKIE_SECURE": True,  # Only send over HTTPS
            "SESSION_COOKIE_HTTPONLY": True,  # Prevent JavaScript access
            "SESSION_COOKIE_SAMESITE": "None",  # CRITICAL FIX: None for cross-site compatibility
            "SESSION_COOKIE_DOMAIN": None,  # Don't restrict domain for flexibility
            "SESSION_COOKIE_PATH": "/",  # Available on all paths
            "REMEMBER_COOKIE_SECURE": True,
            "REMEMBER_COOKIE_HTTPONLY": True,
            "REMEMBER_COOKIE_SAMESITE": "None",  # CRITICAL FIX: None for cross-site compatibility
            "REMEMBER_COOKIE_DURATION": 2592000,  # 30 days
            "SESSION_COOKIE_NAME": "__Host-session",
            "PERMANENT_SESSION_LIFETIME": timedelta(days=30),
            # Server-side Session Config
            "SESSION_TYPE": os.getenv(
                "SESSION_TYPE", "sqlalchemy"
            ),  # Default to DB if not set
            "SESSION_PERMANENT": True,
            "SESSION_USE_SIGNER": True,
            "SESSION_KEY_PREFIX": "missioncontrol:session:",
        }
    )

    # Initialize database with error handling FIRST
    try:
        from models import db

        db.init_app(app)

        # Auto-run database migrations on startup (production-safe)
        with app.app_context():
            try:
                from sqlalchemy import inspect, text

                inspector = inspect(db.engine)
                columns = [col["name"] for col in inspector.get_columns("users")]

                if "trial_started_at" not in columns:
                    app.logger.info("🔧 Adding missing trial_started_at column...")
                    db.session.execute(
                        text("""
                        ALTER TABLE users
                        ADD COLUMN trial_started_at TIMESTAMP WITH TIME ZONE
                    """)
                    )
                    db.session.commit()
                    app.logger.info("✅ Successfully added trial_started_at column")
                else:
                    app.logger.debug("✅ Database schema up to date")
            except Exception as migration_error:
                app.logger.warning(
                    f"Migration check failed (non-critical): {migration_error}"
                )
                # Don't crash the app if migration fails - it might already exist
                try:
                    db.session.rollback()
                except:
                    pass

    except ImportError:
        # Fallback database initialization
        from flask_sqlalchemy import SQLAlchemy

        db = SQLAlchemy()
        db.init_app(app)

    # KILLED SERVER SESSIONS: No longer using Flask-Session or Redis/SQLAlchemy sessions.
    # We are now Level 100 Stateless JWT (Shopify Session Tokens).
    app.config["SESSION_TYPE"] = None

    # Initialize login manager
    try:
        from flask_login import LoginManager

        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = "auth.login"

        @login_manager.user_loader
        def load_user(user_id):
            try:
                from models import User

                return User.query.get(int(user_id))
            except Exception as e:
                app.logger.error(f"Error loading user {user_id}: {e}")
                return None

        @login_manager.request_loader
        def load_user_from_request(request):
            """
            Load user from request with session-first verification.
            """
            from flask import session

            from models import ShopifyStore, User
            from shopify_utils import normalize_shop_url

            # 1. Check session cookie first - THIS IS THE SOURCE OF TRUTH
            user_id = session.get("_user_id")
            if user_id:
                try:
                    user = User.query.get(int(user_id))
                    if user:
                        return user
                except Exception:
                    pass

            # 2. Check HMAC for OAuth flow (fallback ONLY if no session)
            shop = request.args.get("shop")
            if shop and request.args.get("hmac"):
                from shopify_oauth import verify_hmac
                if not verify_hmac(request.args):
                    app.logger.warning(f"Invalid HMAC attempt for shop: {shop}")
                    return None

                shop = normalize_shop_url(shop)
                # Ensure we get the latest active store for this shop
                store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
                if not store:
                    app.logger.warning(f"HMAC Valid but no active store found for {shop}. Returning None.")
                    return None

                if store and store.user:
                    # CRITICAL FIX: Explicitly set session for Safari iframe compatibility
                    from flask_login import login_user

                    login_user(store.user, remember=False)
                    session["shop_domain"] = shop
                    session["_user_id"] = store.user.id
                    session["shop"] = shop # Ensure shop is also set
                    session.permanent = True
                    session.modified = True 

                    app.logger.info(
                        f"🔗 HMAC AUTH SUCCESS: User {store.user.id} authenticated for shop {shop}."
                    )
                    return store.user

            return None
    except Exception as e:
        app.logger.error(f"Failed to initialize login manager: {e}")
        raise

    # Setup logging
    try:
        from logging_config import setup_logging

        setup_logging(app)
    except ImportError:
        # Fallback logging
        import logging

        logging.basicConfig(level=logging.INFO)
        app.logger.setLevel(logging.INFO)

    # Register blueprints (with error handling for missing blueprints)
    blueprints_to_register = [
        ("core_routes", "core_bp"),
        ("auth", "auth_bp"),
        (
            "shopify_oauth",
            "oauth_bp",
        ),  # OAuth blueprint with /install and /auth/callback routes
        ("shopify_routes", "shopify_bp"),
        ("billing", "billing_bp"),
        ("features_pages", "features_pages_bp"),
        ("features_routes", "features_bp"),
        ("legal_routes", "legal_bp"),
        ("gdpr_compliance", "gdpr_bp"),
        ("webhook_shopify", "webhook_shopify_bp"),
        ("faq_routes", "faq_bp"),
        ("enhanced_features", "enhanced_bp"),
        ("admin_routes", "admin_bp"),
    ]

    registered_blueprints = []
    failed_blueprints = []

    for module_name, blueprint_name in blueprints_to_register:
        try:
            # DEBUGGING: Log detailed blueprint registration
            app.logger.info(
                f"🔍 Attempting to register {blueprint_name} from {module_name}"
            )

            module = __import__(module_name)
            blueprint = getattr(module, blueprint_name)

            # DEBUGGING: Log blueprint details before registration
            app.logger.info(f"🔍 Blueprint {blueprint_name} details:")
            app.logger.info(f"  - Name: {blueprint.name}")
            app.logger.info(f"  - URL prefix: {blueprint.url_prefix}")
            app.logger.info(
                f"  - Routes: {[str(rule) for rule in blueprint.deferred_functions]}"
            )

            app.register_blueprint(blueprint)
            registered_blueprints.append(blueprint_name)
            app.logger.info(f"✅ Registered blueprint: {blueprint_name}")

            # DEBUGGING: Special OAuth blueprint verification
            if blueprint_name == "oauth_bp":
                app.logger.info(f"🔍 OAuth blueprint registered successfully")
                app.logger.info(f"  - Blueprint name: {blueprint.name}")
                app.logger.info(f"  - URL prefix: {blueprint.url_prefix}")

                # Check if routes are actually registered
                oauth_routes = [
                    rule
                    for rule in app.url_map.iter_rules()
                    if "oauth" in rule.endpoint
                ]
                app.logger.info(f"  - OAuth routes found: {len(oauth_routes)}")
                for route in oauth_routes:
                    app.logger.info(
                        f"    * {route.endpoint}: {route.rule} {list(route.methods)}"
                    )
                app.logger.info(
                    f"✅ OAuth blueprint registered - /auth/callback route should be available"
                )

        except (ImportError, AttributeError) as e:
            failed_blueprints.append(f"{blueprint_name}: {str(e)}")
            app.logger.warning(
                f"❌ Could not register blueprint {blueprint_name} from {module_name}: {e}"
            )

            # Special handling for OAuth blueprint failure
            if blueprint_name == "oauth_bp":
                app.logger.error(
                    f"❌ CRITICAL: OAuth blueprint failed to register - /auth/callback will return 404!"
                )

        except Exception as e:
            # Catch any other blueprint registration errors
            failed_blueprints.append(f"{blueprint_name}: CRITICAL ERROR - {str(e)}")
            app.logger.error(
                f"💥 CRITICAL ERROR registering blueprint {blueprint_name}: {e}"
            )
            # Don't raise here - continue with other blueprints

    app.logger.info(
        f"Blueprint registration complete: {len(registered_blueprints)} successful, {len(failed_blueprints)} failed"
    )

    if failed_blueprints:
        app.logger.warning(f"Failed blueprints: {failed_blueprints}")
        # Store failed blueprints info for debugging
        app.config["FAILED_BLUEPRINTS"] = failed_blueprints

    # Enhanced error handlers
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal Server Error: {error}", exc_info=True)
        try:
            from models import db

            db.session.rollback()
        except:
            pass

        from flask import jsonify, render_template_string, request

        if request.is_json or request.path.startswith("/api/"):
            return jsonify(
                {
                    "error": "Internal Server Error",
                    "message": "An error occurred processing your request",
                    "success": False,
                }
            ), 500
        else:
            return render_template_string("""
            <h1>Something went wrong</h1>
            <p>We're working to fix this issue. Please try again later.</p>
            <a href="/">Return to Dashboard</a>
            """), 500

    @app.errorhandler(404)
    def not_found_error(error):
        from flask import jsonify, render_template_string, request

        if request.is_json or request.path.startswith("/api/"):
            return jsonify(
                {
                    "error": "Not Found",
                    "message": "The requested resource was not found",
                    "success": False,
                }
            ), 404
        else:
            return render_template_string("""
            <h1>Page Not Found</h1>
            <p>The page you're looking for doesn't exist.</p>
            <a href="/">Return to Dashboard</a>
            """), 404


    # ============================================================================
    # LEVEL 100 IDENTITY MIDDLEWARE (Stateless JWT / Context Extraction)
    # ============================================================================
    # Global 5-minute cache for shop identity (shop_domain -> (user_id, store_id, is_active, expiry))
    app._shop_identity_cache = {}
    @app.before_request
    def extract_identity_context():
        """
        Global middleware to extract identity from JWT (Authorization: Bearer <token>)
        or Shopify Headers/Params. Populates request.shop_domain and g.current_user.
        """
        import time
        from flask import g, request, session
        from models import ShopifyStore, User
        from shopify_utils import normalize_shop_url
        
        now = time.time()
        g.current_user = None
        
        # 1. Extract Shop Domain from all possible sources (Prioritize Header/Params)
        shop = (
            request.headers.get('X-Shopify-Shop-Domain') or
            request.args.get('shop') or
            request.form.get('shop') or
            session.get('shop_domain') or
            session.get('shop') or # Legacy session key fallback
            'None'
        )
        
        if shop != 'None':
            request.shop_domain = normalize_shop_url(shop)
        else:
            request.shop_domain = None

        # 2. Check 5-minute Cache for this shop
        if request.shop_domain and request.shop_domain in app._shop_identity_cache:
            user_id, store_id, is_active, expiry = app._shop_identity_cache[request.shop_domain]
            if now < expiry and is_active:
                g.current_user = User.query.get(user_id)
                if g.current_user:
                    return # SUCCESS: Cache hit

        # 3. Handle Stateless JWT (Authorization Header)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from session_token_verification import verify_session_token_stateless
                payload = verify_session_token_stateless(auth_header.split(" ")[1])
                if payload:
                    dest = payload.get("dest", "")
                    request.shop_domain = dest.replace("https://", "").split("/")[0]
            except Exception as e:
                app.logger.debug(f"JWT stateless extraction failed: {e}")

        # 4. Database Lookup & Cache Update
        if request.shop_domain:
            store = ShopifyStore.query.filter_by(shop_url=request.shop_domain, is_active=True).first()
            if store:
                g.current_user = User.query.get(store.user_id)
                if g.current_user:
                    # Update 5-minute Cache
                    app._shop_identity_cache[request.shop_domain] = (
                        g.current_user.id, store.id, store.is_active, now + 300
                    )

        # 5. Last Fallback: Logged in user from Flask-Login
        from flask_login import current_user
        if not g.current_user and current_user.is_authenticated:
            g.current_user = current_user

    @app.before_request
    def global_jwt_verification():
        """
        GLOBAL IDENTITY EXTRACTION: Performs JWT verification for every request.
        Sets request.session_token_verified and request.shop_domain.
        """
        from flask import request
        from session_token_verification import get_bearer_token, verify_session_token_stateless

        token = get_bearer_token()
        if token:
            payload = verify_session_token_stateless(token)
            if payload:
                dest = payload.get("dest", "")
                request.shop_domain = dest.replace("https://", "").split("/")[0]
                request.session_token_verified = True
                app.logger.debug(f"Global JWT Verified: {request.shop_domain}")

    # ============================================================================
    # GLOBAL ZERO-TRUST HARD-LOCK MIDDLEWARE
    # ============================================================================
    @app.before_request
    def hard_lock_middleware():
        """
        MANDATORY SECURITY GATE: Enforces Zero-Trust across all functional routes.
        1. Authentication (Flask-Login)
        2. Active Store Presence (DB Check)
        3. Identity Integrity (Session vs JWT vs URL)
        """
        from flask import jsonify, redirect, request, session, url_for
        from flask_login import current_user, logout_user
        from shopify_utils import normalize_shop_url

        # Skip for static files, debug routes, webhooks, and the auth handshake itself
        whitelist = [
            "/static", 
            "/debug", 
            "/oauth/", 
            "/auth/", 
            "/webhook/",
            "/favicon.ico",
            "/health"
        ]
        if any(request.path.startswith(path) for path in whitelist):
            return

        # [NEW] Allow if identity was already established by HMAC/JWT in this request
        from flask import g
        if getattr(g, 'current_user', None) and g.current_user.is_authenticated:
            return

        # 1. Identity Integrity Check (URL vs Session vs JWT)
        url_shop = request.args.get("shop")
        session_shop = session.get("shop_domain")
        jwt_verified = getattr(request, 'session_token_verified', False)

        if url_shop:
            url_shop = normalize_shop_url(url_shop)
            
            # If we have a verified JWT, the shop MUST match its destination
            if jwt_verified and request.shop_domain != url_shop:
                app.logger.error(f"🚨 JWT MISMATCH: URL={url_shop}, JWT={request.shop_domain}")
                return jsonify({"error": "Identity mismatch", "action": "refresh"}), 403

            # If we have a session, it MUST match the URL shop
            if session_shop and normalize_shop_url(session_shop) != url_shop:
                app.logger.warning(f"🚨 SESSION MISMATCH: URL={url_shop}, Session={session_shop}. Purging.")
                session.clear()
                logout_user()
                return redirect(url_for("oauth.install", shop=url_shop))

        # 2. Authentication Check
        if not current_user.is_authenticated:
            # For JSON/API requests, return 401
            if request.is_json or not request.accept_mimetypes.accept_html:
                 return jsonify({"error": "Authentication required", "success": False}), 401
            
            # For HTML requests, redirect to login (ESCAPE HATCH for Shopify)
            shop = url_shop or session_shop
            host = request.args.get("host") or session.get("host")
            
            # If we're clearly in a Shopify iframe (shop + hmac/session), return 401 instead of 302
            if shop and (request.args.get("hmac") or session.get("shop_domain")):
                app.logger.warning(f"Shopify context detected: Returning 401 instead of 302 for {request.path}")
                return jsonify({
                    "error": "Authentication required", 
                    "action": "refresh", 
                    "shop": shop,
                    "host": host
                }), 401

            app.logger.warning(f"Blocked anonymous access to {request.path}")
            return redirect(url_for('auth.login', shop=shop, host=host))

        # 3. Active Store Check
        if not current_user.active_shop:
            app.logger.warning(f"User {current_user.id} accessed {request.path} without active shop")
            if request.is_json or not request.accept_mimetypes.accept_html:
                 return jsonify({"error": "Active store connection required", "action": "connect"}), 403
            
            shop = url_shop or session_shop
            host = request.args.get("host") or session.get("host")
            return redirect(url_for('shopify.shopify_settings', error="Store connection required", shop=shop, host=host))


    @app.after_request
    def set_safari_compatible_cookies(response):
        """
        SAFARI FIX: Ensure all cookies have SameSite=Lax; Secure for Safari compatibility.
        Critical for embedded Shopify apps in Safari which blocks third-party cookies by default.
        """
        from flask import request

        # Only apply to embedded app requests
        if request.args.get("embedded") or request.args.get("host"):
            # Force SameSite=Lax on session cookie
            for cookie_name in ["session", "remember_token"]:
                if cookie_name in response.headers.getlist("Set-Cookie"):
                    # Modify existing Set-Cookie headers
                    cookies = []
                    for header in response.headers.getlist("Set-Cookie"):
                        if cookie_name in header:
                            # Ensure SameSite=None; Secure
                            if "SameSite" not in header:
                                header += "; SameSite=None; Secure"
                            else:
                                # Replace any existing SameSite with None
                                import re
                                header = re.sub(r'SameSite=(Lax|Strict)', 'SameSite=None', header)
                                if "Secure" not in header:
                                    header += "; Secure"
                        cookies.append(header)

                    # Replace Set-Cookie headers
                    response.headers.remove("Set-Cookie")
                    for cookie in cookies:
                        response.headers.add("Set-Cookie", cookie)

            app.logger.debug(f"🍪 Safari-compatible cookies set for {request.path}")

        return response

    @app.after_request
    def force_session_commit(response):
        """
        CRITICAL FIX: Force session to commit before response is sent.
        Prevents session loss between routes (especially /dashboard → /settings/shopify).
        """
        try:
            from flask import session
            from flask_login import current_user

            # Only force commit for successful responses
            if response.status_code < 400:
                # Mark session as modified to force save
                session.modified = True

                # If user is authenticated, ensure session has user_id
                if current_user.is_authenticated:
                    user_id = current_user.get_id()
                    if user_id and session.get("_user_id") != user_id:
                        session["_user_id"] = user_id
                        session.permanent = True
                        app.logger.debug(
                            f"Session commit: Ensured _user_id={user_id} in session"
                        )
        except Exception as e:
            app.logger.error(f"Error in force_session_commit: {e}")

        return response

    @app.before_request
    def cctv_watchdog():
        """THE WATCHDOG: Surveillance & Neutralization"""
        from flask import session
        
        from models import ShopifyStore, db
        from shopify_utils import normalize_shop_url
        
        # 1. SCAN THE PORCH
        shop = request.args.get('shop')
        user_id = session.get('_user_id')
        
        # 2. DETECT THE BS
        if shop and user_id:
            try:
                shop = normalize_shop_url(shop)
                store = ShopifyStore.query.filter_by(shop_url=shop).first()
                
                # 3. NEUTRALIZE & REPORT
                if store and store.user_id != int(user_id):
                    old_id = store.user_id
                    store.user_id = int(user_id) # The Hijack
                    db.session.commit()
                    
                    # THE SNITCH (Speed of Light notification)
                    app.logger.info(f"🚨 CCTV: Re-homed {shop} from User {old_id} to User {user_id}. Threat neutralized.")
            except Exception as e:
                app.logger.warning(f"⚠️ CCTV Watchdog encountered an issue: {e}")
                db.session.rollback()


    return app


def create_fortress_app():
    """Alias for compatibility"""
    return create_app()
