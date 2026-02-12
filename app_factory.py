"""
Simple App Factory
"""

import logging
import os
import time
import signal
import sys
import traceback
from datetime import timedelta

from flask import Flask, request, jsonify, g, session, redirect, url_for, render_template_string, current_app
from werkzeug.middleware.proxy_fix import ProxyFix
from models import db, User, ShopifyStore


def create_app():
    """Create Flask app with comprehensive error handling"""
    app = Flask(__name__)
    app.static_folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), "static")
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
            "SESSION_COOKIE_SECURE": True,    # CRITICAL: Mandatory for SameSite=None
            "SESSION_COOKIE_HTTPONLY": True,  # Prevent JavaScript access
            "SESSION_COOKIE_SAMESITE": "None",  # CRITICAL: Mandatory for Embedded Apps
            "SESSION_COOKIE_DOMAIN": None,  # Don't restrict domain for flexibility
            "SESSION_COOKIE_PATH": "/",  # Available on all paths
            "REMEMBER_COOKIE_SECURE": True,
            "REMEMBER_COOKIE_HTTPONLY": True,
            "REMEMBER_COOKIE_SAMESITE": "None",  # CRITICAL FIX: None for cross-site compatibility
            "REMEMBER_COOKIE_DURATION": 2592000,  # 30 days
            "SESSION_COOKIE_NAME": "__Host-session",
            "PERMANENT_SESSION_LIFETIME": timedelta(days=7),  # Safari Grace: 7 days for iframe
            # Server-side Session Config
            "SESSION_TYPE": os.getenv(
                "SESSION_TYPE", "sqlalchemy"
            ),  # Default to DB if not set
            "SESSION_PERMANENT": True,
            "SESSION_USE_SIGNER": True,
            "SESSION_KEY_PREFIX": "missioncontrol:session:",
            # TITAN: Static Asset Latency Fix
            "SEND_FILE_MAX_AGE_DEFAULT": 31536000,  # 1 year caching for CSS/JS
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

                if "current_store_id" not in columns:
                    app.logger.info("🔧 Adding missing current_store_id column to users...")
                    db.session.execute(
                        text("""
                        ALTER TABLE users
                        ADD COLUMN current_store_id INTEGER REFERENCES shopify_stores(id) ON DELETE SET NULL
                    """)
                    )
                    db.session.commit()
                    app.logger.info("✅ Successfully added current_store_id column")
                
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
            Load user from request - LEVEL 100 Stateless JWT (Shopify Session Tokens).
            Mandatory: RETURN None on failure, NEVER redirect().
            """
            from sqlalchemy.orm import joinedload
            from models import User, ShopifyStore, db

            # 1. TITAN: Trust id_token (JWT) from Shopify - Absolute Priority
            id_token = request.args.get("id_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
            if id_token:
                try:
                    from session_token_verification import verify_session_token_stateless
                    payload = verify_session_token_stateless(id_token)
                    if payload:
                        # sub is the Shopify User ID / Shop Domain linkage
                        shop = payload.get("dest", "").replace("https://", "").split("/")[0]
                        if shop:
                            # Flag request as verified for middleware downstream
                            request.session_token_verified = True
                            request.shop_domain = shop
                            
                            # [RE-WELD] Priority 1: Active Store
                            store = db.session.query(ShopifyStore).options(joinedload(ShopifyStore.user)).filter(
                                ShopifyStore.shop_url == shop, 
                                ShopifyStore.is_active == True
                            ).first()
                            
                            # [RE-WELD] Priority 2: Inactive Store (Deep Recovery)
                            if not store:
                                store = db.session.query(ShopifyStore).options(joinedload(ShopifyStore.user)).filter(
                                    ShopifyStore.shop_url == shop
                                ).first()
                                if store:
                                    app.logger.info(f"TITAN [RE-WELD] JWT Valid, recovered User {store.user_id} via inactive Store {shop}")

                            if store and store.user:
                                app.logger.info(f"TITAN [JWT_TRUST] Authenticated User {store.user.id} via id_token")
                                
                                # FIX FLIP-FLOP: Persist verification in session
                                from flask_login import login_user
                                login_user(store.user, remember=False)
                                
                                # Set session to prevent re-verification on every request
                                session["_user_id"] = store.user.id
                                session["shop_domain"] = shop
                                session["shop"] = shop
                                session.permanent = True
                                session.modified = True
                                
                                # Memoize for this request
                                g.current_user = store.user
                                g.current_store = store
                                
                                return store.user
                except Exception as je:
                    app.logger.debug(f"Seamless id_token trust failed: {je}")

            # 2. Check session cookie - FALLBACK
            user_id = session.get("_user_id")
            if user_id:
                try:
                    # [LATENCY CRUSH] Fetch User and their Welded Store in a SINGLE JOIN
                    user = db.session.query(User).options(joinedload(User.current_store)).get(int(user_id))
                    if user:
                        # Memoize for global access
                        g.current_store = user.current_store
                        # Sync shop_domain to request for middleware consistency
                        if user.current_store:
                            request.shop_domain = user.current_store.shop_url
                        return user
                except Exception as e:
                    app.logger.debug(f"Session-based user load failed: {e}")

            # 3. Check HMAC for OAuth flow (fallback)
            shop = request.args.get("shop")
            if shop and request.args.get("hmac"):
                from shopify_oauth import verify_hmac
                if not verify_hmac(request.args):
                    app.logger.warning(f"Invalid HMAC attempt for shop: {shop}")
                    return None

                from shopify_utils import normalize_shop_url
                shop = normalize_shop_url(shop)
                from config import DEV_SHOP_DOMAIN
                
                # [RE-WELD] Priority 1: Active Store
                store = db.session.query(ShopifyStore).options(joinedload(ShopifyStore.user)).filter(
                    ShopifyStore.shop_url == shop, 
                    ShopifyStore.is_active == True
                ).first()
                
                # [RE-WELD] Priority 2: Inactive Store (Deep Recovery)
                if not store:
                    store = db.session.query(ShopifyStore).options(joinedload(ShopifyStore.user)).filter(
                        ShopifyStore.shop_url == shop
                    ).first()
                    if store:
                        app.logger.info(f"TITAN [RE-WELD] HMAC Valid, recovered User {store.user_id} via inactive Store {shop}")

                if store and store.user:
                    from flask_login import login_user
                    login_user(store.user, remember=False)
                    
                    # [TITAN] Global Memoization
                    g.current_user = store.user
                    g.current_store = store
                    
                    request.shop_domain = shop
                    session["shop_domain"] = shop
                    session["_user_id"] = store.user.id
                    session["shop"] = shop
                    session.permanent = True
                    session.modified = True 

                    app.logger.info(f"🔗 HMAC AUTH SUCCESS: User {store.user.id} authenticated for shop {shop}.")
                    return store.user
                else:
                    app.logger.error(f"HMAC Valid for {shop} but associated user is missing.")
                    return None

            return None
    except Exception as e:
        app.logger.error(f"Failed to initialize login manager: {e}")
        raise

    # Setup logging
    try:
        from logging_config import setup_logging
        setup_logging(app)
    except ImportError:
        logging.basicConfig(level=logging.INFO)
        app.logger.setLevel(logging.INFO)

    # ============================================================================
    # TITAN MONITORING: Global Observer Layer
    # ============================================================================
    @app.before_request
    def titan_observer_before():
        """TITAN: Record start time and log incoming request"""
        # Generate unique request ID for log correlation
        from unified_error_boundary import generate_request_id
        request_id = generate_request_id()
        
        # FAST TRACK: Bypass heavy logging for health check monitors (eliminate 600-700ms latency)
        user_agent = request.headers.get('User-Agent', '')
        if request.path == '/health' or 'Render' in user_agent or 'UptimeRobot' in user_agent:
            # DEBUG level for noise
            app.logger.debug(f"HEALTH_CHECK [{request_id}] {request.method} {request.path}")
            return None
        
        # Skip static assets (DEBUG level)
        if request.path.startswith('/static/') or request.path.endswith('.ico'):
            app.logger.debug(f"STATIC [{request_id}] {request.path}")
            return None
        
        g.titan_start_time = time.time()
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # INFO level for normal requests
        app.logger.info(
            f"TITAN [HIT] [{request_id}] {request.method} {request.path} | IP: {client_ip} | Referer: {request.referrer}"
        )

    @app.after_request
    def titan_observer_after(response):
        """TITAN: Calculate latency and log response status"""
        from unified_error_boundary import generate_request_id
        request_id = generate_request_id()
        
        # SILENCE THE NOISE: Don't log 200 OKs for health checks
        if request.path == '/health' and response.status_code == 200:
            return response
        
        if hasattr(g, 'titan_start_time'):
            latency = time.time() - g.titan_start_time
            latency_ms = int(latency * 1000)
            
            # Metadata enrichment
            shop = getattr(g, 'shop_domain', request.args.get('shop', 'NONE'))
            user_id = getattr(g, 'user_id', 'NONE')
            status_code = response.status_code
            
            # Log level classification
            if status_code >= 500:
                # CRITICAL: Server errors
                app.logger.critical(
                    f"TITAN [OUT] [{request_id}] {request.method} {request.path} | "
                    f"Status: {status_code} | Latency: {latency_ms}ms | "
                    f"User: {user_id} | Shop: {shop}"
                )
            elif status_code >= 400:
                # WARNING: Client errors
                app.logger.warning(
                    f"TITAN [OUT] [{request_id}] {request.method} {request.path} | "
                    f"Status: {status_code} | Latency: {latency_ms}ms | "
                    f"User: {user_id} | Shop: {shop}"
                )
            else:
                # INFO: Success
                app.logger.info(
                    f"TITAN [OUT] [{request_id}] {request.method} {request.path} | "
                    f"Status: {status_code} | Latency: {latency_ms}ms | "
                    f"User: {user_id} | Shop: {shop}"
                )
        return response

    # ============================================================================
    # TITAN: Sentinel System Handlers
    # ============================================================================
    @app.errorhandler(404)
    def titan_404_handler(error):
        """TITAN: Enhanced 404 handler with referer tracking and security audit"""
        from unified_error_boundary import generate_request_id
        request_id = generate_request_id()
        
        # Classify: WARNING for API routes, DEBUG for assets
        is_api_route = request.path.startswith('/api/') or request.path.startswith('/settings/')
        is_asset = request.path.startswith('/static/') or request.path.endswith(('.ico', '.css', '.js', '.png', '.jpg'))
        
        shop = request.args.get('shop', 'NONE')
        referer = request.referrer or 'NONE'
        
        if is_api_route:
            # WARNING: Missing API endpoint
            app.logger.warning(
                f"🚧 MISSING_API_ROUTE [{request_id}] {request.method} {request.url} | "
                f"Referer: {referer} | Shop: {shop}"
            )
            
            # Log to security audit
            try:
                from security_audit import audit_logger
                audit_logger.warning(
                    f"404 on API route: {request.path} | Referer: {referer} | Shop: {shop}"
                )
            except ImportError:
                pass
                
        elif is_asset:
            # DEBUG: Missing static asset
            app.logger.debug(f"MISSING_ASSET [{request_id}] {request.path} | Referer: {referer}")
        else:
            # INFO: Missing regular page
            app.logger.info(f"MISSING_PAGE [{request_id}] {request.path} | Referer: {referer}")
        
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource does not exist on the Titan node.',
            'path': request.path,
            'request_id': request_id
        }), 404

    @app.errorhandler(Exception)
    @app.errorhandler(500)
    def titan_500_handler(error):
        """TITAN: Critical capture of all system crashes"""
        tb = traceback.format_exc()
        app.logger.critical(
            f"TITAN [CRASH] {request.method} {request.path}\n{tb}"
        )
        
        try:
            from models import db
            db.session.rollback()
        except:
            pass

        return jsonify({
            "error": "Titan System Failure",
            "message": "An internal error was caught and logged by the Titan Observer.",
            "traceback": tb.splitlines()[-1] if tb else "No traceback",
            "success": False
        }), 500

    # TITAN: Last Breath Signal Handler
    def titan_last_breath(sig, frame):
        app.logger.info(f"TITAN [SIGNAL] Process {os.getpid()} received {sig}. Taking last breath... Reap confirmed.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, titan_last_breath)
    signal.signal(signal.SIGINT, titan_last_breath)    
    # === CONTEXT PROCESSORS ===
    @app.context_processor
    def inject_sentinel():
        """
        Sentinel Bot: Conditional diagnostic script injection
        Activate via ?sentinel_mode=true or for specific test users
        SKIP injection if token already present (prevents over-injection)
        """
        from flask import request
        from flask_login import current_user
        
        # FIX: Skip Sentinel if token already present in URL or headers
        id_token_in_url = request.args.get('id_token')
        auth_header = request.headers.get('Authorization')
        has_token = bool(id_token_in_url or auth_header)
        
        if has_token:
            # Token present, Sentinel not needed
            return dict(show_sentinel=False)
        
        # Check query parameter
        sentinel_via_param = request.args.get('sentinel_mode') == 'true'
        
        # Check for specific test user (User 11 for JWT diagnostics)
        sentinel_via_user = False
        if current_user and current_user.is_authenticated:
            # Only inject for User 11 (test account)
            sentinel_via_user = getattr(current_user, 'id', None) == 11
        
        show_sentinel = sentinel_via_param or sentinel_via_user
        
        if show_sentinel:
            app.logger.info(f"🤖 Sentinel Bot activated | Param: {sentinel_via_param} | User: {sentinel_via_user}")
        
        return dict(show_sentinel=show_sentinel)
    
    @app.context_processor
    def inject_shopify_config():
        """Globally inject Shopify Config for App Bridge 3.0+ actions"""
        return {
            "SHOPIFY_API_KEY": os.getenv("SHOPIFY_API_KEY", "")
        }

    # Register blueprints (with error handling for missing blueprints)
    blueprints_to_register = [
        ("shopify_oauth", "oauth_bp"),  # OAuth flow
        ("core_routes", "core_bp"),
        ("shopify_routes", "shopify_bp"),
        ("webhook_shopify", "webhook_shopify_bp"),
        ("client_telemetry", "client_telemetry_bp"),  # Client-side telemetry
        ("billing", "billing_bp"),             # Shopify subscription billing
        ("legal_routes", "legal_bp"),  # Privacy/Terms pages
        ("faq_routes", "faq_bp"),
        ("enhanced_features", "enhanced_bp"),
        ("admin_routes", "admin_bp"),
        ("telemetry_routes", "telemetry_bp"),  # Sentinel Bot endpoint
        # Removed: help_routes, profile_routes (files don't exist)
    ]

    registered_blueprints = []
    failed_blueprints = []

    for module_name, blueprint_name in blueprints_to_register:
        try:
            module = __import__(module_name)
            blueprint = getattr(module, blueprint_name)

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

    # Titan Sentinel Handlers have replaced legacy handlers.


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
        # [EBAY-LEVEL] Skip identity checks for static files (Performance + Crash Prevention)
        if request.endpoint == 'static' or request.path.startswith(('/static', '/health')):
            return
        
        import time
        from models import User, ShopifyStore, db  # Added db to prevent UnboundLocalError
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
                try:
                    from sqlalchemy.orm import joinedload
                    # [LATENCY CRUSH] Single Join lookup for cached hit
                    g.current_user = db.session.query(User).options(joinedload(User.current_store)).get(user_id)
                    if g.current_user:
                        g.current_store = g.current_user.current_store
                        return # SUCCESS: Cache hit
                except Exception as e:
                    # [PRODUCTION HARDENING] Graceful degradation on DB hiccup
                    app.logger.error(f"Identity cache lookup failed: {e}")
                    g.current_user = None

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
            try:
                from models import db
                from sqlalchemy.orm import joinedload
                # [HOTFIX] Explicit and Clean Lookup to avoid ambiguous FK stalls
                store = db.session.query(ShopifyStore).options(joinedload(ShopifyStore.user)).filter(
                    ShopifyStore.shop_url == request.shop_domain,
                    ShopifyStore.is_active == True
                ).first()
                
                if store and store.user:
                    g.current_user = store.user
                    g.current_store = store # TITAN MEMOIZATION
                    # Update 5-minute Cache
                    app._shop_identity_cache[request.shop_domain] = (
                        g.current_user.id, store.id, store.is_active, now + 300
                    )
            except Exception as e:
                # [PRODUCTION HARDENING] Graceful degradation on DB hiccup (SSL connection errors, etc.)
                app.logger.error(f"Identity extraction DB lookup failed: {e}")
                g.current_user = None

        # 5. Last Fallback: Logged in user from Flask-Login
        # Ensure we don't overwrite the global current_user proxy
        from flask_login import current_user as login_manager_user
        
        # FIX: Check the login manager status safely
        is_authed = False
        try:
            is_authed = login_manager_user.is_authenticated
        except AttributeError:
            is_authed = False

        if not g.get('current_user') and is_authed:
            g.current_user = login_manager_user

    @app.before_request
    def global_jwt_verification():
        """
        GLOBAL IDENTITY EXTRACTION: Performs JWT verification for every request.
        Sets request.session_token_verified and request.shop_domain.
        Also performs GLOBAL IDENTITY SYNC to ensure current_user matches JWT.
        """
        from flask import request
        from flask_login import current_user, login_user
        from models import ShopifyStore
        from session_token_verification import get_bearer_token, verify_session_token_stateless

        token = get_bearer_token() or request.args.get("id_token")
        if token:
            payload = verify_session_token_stateless(token)
            if payload:
                # [FINALITY] Extract shop domain ONLY from 'dest' payload
                dest = payload.get("dest", "")
                if not dest:
                    app.logger.warning("Global JWT verification failed: Missing 'dest' in payload")
                    request.session_token_verified = False
                    return

                shop_domain = dest.replace("https://", "").split("/")[0]
                request.shop_domain = shop_domain
                request.session_token_verified = True
                app.logger.debug(f"Global JWT Verified (Legend Tier): {shop_domain}")
                
                # GLOBAL IDENTITY SYNC
                try:
                    from config import DEV_SHOP_DOMAIN
                    # Try active store, but allow Dev Safe-Pass
                    store = ShopifyStore.query.filter_by(shop_url=shop_domain, is_active=True).first()
                    if not store and shop_domain == DEV_SHOP_DOMAIN:
                        store = ShopifyStore.query.filter_by(shop_url=shop_domain).first()
                        
                    if store and store.user:
                        if not current_user.is_authenticated or current_user.id != store.user.id:
                            app.logger.info(f"Identity Sync (Global JWT): Logging in {store.user.id} for {shop_domain}")
                            login_user(store.user)
                except Exception as e:
                    app.logger.error(f"Global Identity Sync error: {e}")
            else:
                # Token present but invalid
                request.session_token_verified = False
                app.logger.warning("Global JWT verification failed: Invalid token")
        else:
            # Fallback for manual check if needed
            request.session_token_verified = getattr(request, 'session_token_verified', False)

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

        # [LOOP-BREAKER] Strict Endpoint Whitelisting
        # request.endpoint is None for 404s, which is fine to check auth for
        whitelisted_endpoints = [
            'auth.login',
            'oauth.install',
            'oauth.callback',
            'static',
            'webhook_shopify.app_uninstall',
            'webhook_shopify.app_subscription_update',
            'gdpr_compliance.customers_data_request',
            'gdpr_compliance.customers_redact',
            'gdpr_compliance.shop_redact',
            'health'
        ]
        
        # 1. Allow Whitelisted Endpoints immediately
        if request.endpoint in whitelisted_endpoints:
            return

        # 2. Allow path-based overrides for extra safety
        whitelist_paths = ["/static", "/debug", "/oauth/", "/auth/", "/webhook/", "/favicon.ico", "/health"]
        if any(request.path.startswith(path) for path in whitelist_paths):
            return

        # [NEW] Allow if identity was already established by HMAC/JWT in this request
        from flask import g
        if getattr(g, 'current_user', None) and g.current_user.is_authenticated:
            return

        # 3. Identity Integrity Check (URL vs Session vs JWT)
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
                # Use breakout only if we are absolutely sure we are in a browser context
                if url_shop and not request.is_json:
                    goto_url = url_for("oauth.install", shop=url_shop, _external=True)
                    return f'''
                        <script src="https://unpkg.com/@shopify/app-bridge@3"></script>
                        <script>
                            if (window.top !== window.self) {{
                                window.top.location.href = "{goto_url}";
                            }} else {{
                                window.location.href = "{goto_url}";
                            }}
                        </script>
                    ''', 200
                return None # Let @login_required handle it

        # [LOCAL HELPER] The Final Weld Handshake
        def trigger_reauth_flow():
            shop = url_shop or session_shop
            if shop:
                app.logger.info(f"🔄 Identity Finality: Triggering re-auth handshake for {shop}")
                # Ensure load_user_from_request is available in scope
                # NEVER return a redirect here, either return a user or None
                return load_user_from_request(request)
            return None

        # 4. The Final Weld: Identity Guard
        from flask_login import current_user as login_manager_user
        user_val = g.get('current_user') or login_manager_user
        
        if not hasattr(user_val, 'is_authenticated') or not user_val.is_authenticated:
            # Attempt one last re-weld before failing
            user_val = trigger_reauth_flow()
            if not user_val or not user_val.is_authenticated:
                if request.is_json:
                    return jsonify({"error": "Authentication required", "action": "reauth"}), 401
                # If we have a shop, we can return None and let @login_required redirect if it's an HTML request
                # BUT the user wants no redirects in the "loader" path.
                return None

        # 5. Active Store Check
        if not user_val.active_shop:
            app.logger.warning(f"User {user_val.id} accessed {request.path} without active shop")
            if request.is_json or not request.accept_mimetypes.accept_html:
                 return jsonify({"error": "Active store connection required", "action": "connect"}), 403
            
            # If we are truly missing a store, we can return None to force a 401/403
            # Or return the install breakout for HTML
            if not request.is_json and url_shop:
                return None # Let the view/decorator handle it


    @app.after_request
    def set_safari_compatible_cookies(response):
        """
        SAFARI FIX: Ensure all cookies have SameSite=Lax; Secure for Safari compatibility.
        Critical for embedded Shopify apps in Safari which blocks third-party cookies by default.
        """
        from flask import request

        # Only apply to embedded app requests
        if request.args.get("embedded") or request.args.get("host"):
            # Force SameSite=None; Secure for Safari compatibility
            session_name = app.config.get("SESSION_COOKIE_NAME", "session")
            for cookie_name in [session_name, "remember_token"]:
                if any(header.startswith(f"{cookie_name}=") for header in response.headers.getlist("Set-Cookie")):
                    # Modify existing Set-Cookie headers
                    cookies = []
                    for header in response.headers.getlist("Set-Cookie"):
                        if header.startswith(f"{cookie_name}="):
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
                if hasattr(current_user, "is_authenticated") and current_user.is_authenticated:
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


    @app.route("/health")
    def health_check():
        """Legend Tier Observability: Verify DB and Redis connectivity"""
        from flask import jsonify
        from models import db
        import redis
        
        status = {"status": "healthy", "database": "unknown", "redis": "unknown"}
        
        # 1. Check Database
        try:
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            status["database"] = "connected"
        except Exception as e:
            app.logger.error(f"Health Check Failure (DB): {e}")
            status["database"] = "error"
            status["status"] = "degraded"
            
        # 2. Check Redis
        try:
            # [REDIS CIRCUIT BREAKER] Only connect if REDIS_URL is explicitly set
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                app.logger.info("🔄 TITAN [REDIS] No REDIS_URL configured, running in bypass mode (direct DB)")
                return jsonify({"status": "healthy", "redis": "disabled"}), 200
            
            r = redis.from_url(redis_url)
            r.ping()
            return jsonify({"status": "healthy", "redis": "connected"}), 200
        except redis.RedisError as e:
            app.logger.warning(f"🔴 TITAN [REDIS] Circuit open. Redis unreachable: {e}")
            return jsonify({"status": "healthy", "redis": "unreachable"}), 200
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            return jsonify({"status": "unhealthy", "error": str(e)}), 500

    return app


def create_fortress_app():
    """Alias for compatibility"""
    return create_app()
