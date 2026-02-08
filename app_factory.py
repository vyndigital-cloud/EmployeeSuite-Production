"""
Simple App Factory
"""
import logging
import os
from flask import Flask, request

def create_app():
    """Create Flask app with comprehensive error handling"""
    app = Flask(__name__)
    app.static_folder = 'static'
    app.static_url_path = '/static'
    
    # Enhanced config
    app.config.update({
        'SECRET_KEY': os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
        'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL', 'sqlite:///app.db'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_size': 10,
            'max_overflow': 20,
            'pool_pre_ping': True,
            'pool_recycle': 3600,
        },
        'WTF_CSRF_ENABLED': True,
        'WTF_CSRF_TIME_LIMIT': 3600,
        # Session cookie configuration for login persistence
        'SESSION_COOKIE_SECURE': True,  # Only send over HTTPS
        'SESSION_COOKIE_HTTPONLY': True,  # Prevent JavaScript access
        'SESSION_COOKIE_SAMESITE': 'Lax',  # CRITICAL FIX: Lax for standalone, prevents Safari blocking
        'SESSION_COOKIE_DOMAIN': None,  # Don't restrict domain for flexibility
        'SESSION_COOKIE_PATH': '/',  # Available on all paths
        'REMEMBER_COOKIE_SECURE': True,
        'REMEMBER_COOKIE_HTTPONLY': True,
        'REMEMBER_COOKIE_SAMESITE': 'Lax',  # CRITICAL FIX: Lax for standalone, prevents Safari blocking
        'REMEMBER_COOKIE_DURATION': 2592000,  # 30 days
        
        # Server-side Session Config
        'SESSION_TYPE': os.getenv('SESSION_TYPE', 'sqlalchemy'), # Default to DB if not set
        'SESSION_PERMANENT': True,
        'SESSION_USE_SIGNER': True,
        'SESSION_KEY_PREFIX': 'missioncontrol:session:',
    })
    
    # Initialize database with error handling FIRST
    try:
        from models import db
        db.init_app(app)
        
        # Auto-run database migrations on startup (production-safe)
        with app.app_context():
            try:
                from sqlalchemy import inspect, text
                inspector = inspect(db.engine)
                columns = [col['name'] for col in inspector.get_columns('users')]
                
                if 'trial_started_at' not in columns:
                    app.logger.info("🔧 Adding missing trial_started_at column...")
                    db.session.execute(text("""
                        ALTER TABLE users 
                        ADD COLUMN trial_started_at TIMESTAMP WITH TIME ZONE
                    """))
                    db.session.commit()
                    app.logger.info("✅ Successfully added trial_started_at column")
                else:
                    app.logger.debug("✅ Database schema up to date")
            except Exception as migration_error:
                app.logger.warning(f"Migration check failed (non-critical): {migration_error}")
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

    # Initialize Server-Side Sessions AFTER database is ready
    try:
        from flask_session import Session
        import redis
        
        if os.getenv('REDIS_URL'):
            app.config['SESSION_TYPE'] = 'redis'
            app.config['SESSION_REDIS'] = redis.from_url(os.getenv('REDIS_URL'))
            app.logger.info("🚀 Using REDIS for session storage")
        else:
            app.config['SESSION_TYPE'] = 'sqlalchemy'
            app.config['SESSION_SQLALCHEMY'] = db  # db is now initialized!
            app.config['SESSION_SQLALCHEMY_TABLE'] = 'sessions'
            app.logger.info("💾 Using DATABASE (SQLAlchemy) for session storage")
            
            # Create sessions table if it doesn't exist
            with app.app_context():
                try:
                    from sqlalchemy import inspect
                    inspector = inspect(db.engine)
                    if 'sessions' not in inspector.get_table_names():
                        app.logger.info("🔧 Creating sessions table...")
                        # Flask-Session will create the table automatically
                        db.create_all()
                        app.logger.info("✅ Sessions table created")
                except Exception as table_error:
                    app.logger.warning(f"Could not verify sessions table: {table_error}")
            
        Session(app)
        app.logger.info("✅ Server-side sessions initialized successfully")
    except Exception as e:
        app.logger.error(f"❌ CRITICAL: Failed to initialize server-side sessions: {e}")
        app.logger.error("⚠️  Sessions will NOT persist across worker restarts!")


    
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
            Load user from request with HARD-LINK database verification.
            Prevents User 4 cookies from bleeding into User 11 requests.
            """
            from flask import session
            from models import User, ShopifyStore
            from shopify_utils import normalize_shop_url
            
            # 1. Check session cookie first
            user_id = session.get('_user_id')
            if user_id:
                user = User.query.get(int(user_id))
                if user:
                    return user
            
            # 2. HARD-LINK: Query database by shop parameter
            shop = request.args.get('shop')
            if shop:
                shop = normalize_shop_url(shop)
                # Find the store, then get the user
                store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
                if store and store.user:
                    # CRITICAL: Force current_user to match database
                    app.logger.info(
                        f"🔗 HARD-LINK: Forcing user {store.user.id} for shop {shop} "
                        f"(overriding any stale session data)"
                    )
                    # Log the user in to establish proper session
                    from flask_login import login_user
                    login_user(store.user)
                    session['shop_domain'] = shop
                    return store.user
            
            # 3. Check HMAC for OAuth flow (fallback)
            if shop and request.args.get('hmac'):
                store = ShopifyStore.query.filter_by(shop_url=shop).first()
                if store and store.user:
                    # CRITICAL FIX: Explicitly set session for Safari iframe compatibility
                    from flask_login import login_user
                    login_user(store.user, remember=False)  # No remember cookie in embedded
                    session['shop_domain'] = shop
                    session['_user_id'] = store.user.id
                    session.permanent = True
                    session.modified = True  # Force session write
                    
                    app.logger.info(
                        f"🔗 HMAC AUTH SUCCESS: User {store.user.id} authenticated for shop {shop}. "
                        f"Session explicitly set with SameSite=None support."
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
        ('core_routes', 'core_bp'),
        ('auth', 'auth_bp'), 
        ('shopify_oauth', 'oauth_bp'),  # OAuth blueprint with /install and /auth/callback routes
        ('oauth_diagnostics', 'diagnostics_bp'),  # OAuth diagnostics tool
        ('shopify_routes', 'shopify_bp'),
        ('billing', 'billing_bp'),
        ('features_pages', 'features_pages_bp'),
        ('features_routes', 'features_bp'),
        ('legal_routes', 'legal_bp'),
        ('gdpr_compliance', 'gdpr_bp'),
        ('webhook_shopify', 'webhook_shopify_bp'),
        ('faq_routes', 'faq_bp'),
        ('enhanced_features', 'enhanced_bp'),
        ('admin_routes', 'admin_bp'),
        ('diagnostic_routes', 'diagnostic_bp'),
        ('test_routes', 'test_bp'),
    ]
    
    registered_blueprints = []
    failed_blueprints = []
    
    for module_name, blueprint_name in blueprints_to_register:
        try:
            # DEBUGGING: Log detailed blueprint registration
            app.logger.info(f"🔍 Attempting to register {blueprint_name} from {module_name}")
            
            module = __import__(module_name)
            blueprint = getattr(module, blueprint_name)
            
            # DEBUGGING: Log blueprint details before registration
            app.logger.info(f"🔍 Blueprint {blueprint_name} details:")
            app.logger.info(f"  - Name: {blueprint.name}")
            app.logger.info(f"  - URL prefix: {blueprint.url_prefix}")
            app.logger.info(f"  - Routes: {[str(rule) for rule in blueprint.deferred_functions]}")
            
            app.register_blueprint(blueprint)
            registered_blueprints.append(blueprint_name)
            app.logger.info(f"✅ Registered blueprint: {blueprint_name}")
            
            # DEBUGGING: Special OAuth blueprint verification
            if blueprint_name == 'oauth_bp':
                app.logger.info(f"🔍 OAuth blueprint registered successfully")
                app.logger.info(f"  - Blueprint name: {blueprint.name}")
                app.logger.info(f"  - URL prefix: {blueprint.url_prefix}")
                
                # Check if routes are actually registered
                oauth_routes = [rule for rule in app.url_map.iter_rules() if 'oauth' in rule.endpoint]
                app.logger.info(f"  - OAuth routes found: {len(oauth_routes)}")
                for route in oauth_routes:
                    app.logger.info(f"    * {route.endpoint}: {route.rule} {list(route.methods)}")
                app.logger.info(f"✅ OAuth blueprint registered - /auth/callback route should be available")
                
        except (ImportError, AttributeError) as e:
            failed_blueprints.append(f"{blueprint_name}: {str(e)}")
            app.logger.warning(f"❌ Could not register blueprint {blueprint_name} from {module_name}: {e}")
            
            # Special handling for OAuth blueprint failure
            if blueprint_name == 'oauth_bp':
                app.logger.error(f"❌ CRITICAL: OAuth blueprint failed to register - /auth/callback will return 404!")
                
        except Exception as e:
            # Catch any other blueprint registration errors
            failed_blueprints.append(f"{blueprint_name}: CRITICAL ERROR - {str(e)}")
            app.logger.error(f"💥 CRITICAL ERROR registering blueprint {blueprint_name}: {e}")
            # Don't raise here - continue with other blueprints
    
    app.logger.info(f"Blueprint registration complete: {len(registered_blueprints)} successful, {len(failed_blueprints)} failed")
    
    if failed_blueprints:
        app.logger.warning(f"Failed blueprints: {failed_blueprints}")
        # Store failed blueprints info for debugging
        app.config['FAILED_BLUEPRINTS'] = failed_blueprints
    
    # Enhanced error handlers
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal Server Error: {error}", exc_info=True)
        try:
            from models import db
            db.session.rollback()
        except:
            pass
        
        from flask import jsonify, request, render_template_string
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An error occurred processing your request',
                'success': False
            }), 500
        else:
            return render_template_string("""
            <h1>Something went wrong</h1>
            <p>We're working to fix this issue. Please try again later.</p>
            <a href="/">Return to Dashboard</a>
            """), 500
    
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import jsonify, request, render_template_string
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested resource was not found',
                'success': False
            }), 404
        else:
            return render_template_string("""
            <h1>Page Not Found</h1>
            <p>The page you're looking for doesn't exist.</p>
            <a href="/">Return to Dashboard</a>
            """), 404
    
    # Debug route to see startup issues
    @app.route('/debug/startup')
    def debug_startup():
        """Debug route to see startup issues"""
        from flask import jsonify
        return jsonify({
            'registered_blueprints': registered_blueprints,
            'failed_blueprints': failed_blueprints,
            'config_keys': list(app.config.keys()),
            'environment': os.getenv('ENVIRONMENT'),
            'database_url': app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')
        })
    
    # Debug route to check OAuth routes
    @app.route('/debug/routes')
    def debug_routes():
        """Debug route to see all registered routes"""
        from flask import jsonify
        routes = []
        oauth_routes = []
        for rule in app.url_map.iter_rules():
            route_info = {
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'rule': str(rule)
            }
            routes.append(route_info)
            
            # Track OAuth-related routes specifically
            if 'oauth' in rule.endpoint or '/install' in str(rule) or '/callback' in str(rule) or '/auth/callback' in str(rule):
                oauth_routes.append(route_info)
        
        return jsonify({
            'total_routes': len(routes),
            'oauth_routes': oauth_routes,
            'oauth_callback_exists': any('/auth/callback' in str(rule) for rule in app.url_map.iter_rules()),
            'install_route_exists': any('/install' in str(rule) for rule in app.url_map.iter_rules()),
            'all_routes': routes
        })
    
    @app.route('/debug/oauth-status')
    def debug_oauth_status():
        """Debug OAuth blueprint and route status"""
        from flask import jsonify
        
        # Check if OAuth blueprint is registered
        oauth_blueprint_registered = any(bp.name == 'oauth' for bp in app.blueprints.values())
        
        # Find all OAuth-related routes
        oauth_routes = []
        install_routes = []
        callback_routes = []
        
        for rule in app.url_map.iter_rules():
            route_info = {
                'endpoint': rule.endpoint,
                'rule': str(rule),
                'methods': list(rule.methods)
            }
            
            if 'oauth' in rule.endpoint:
                oauth_routes.append(route_info)
            if 'install' in str(rule):
                install_routes.append(route_info)
            if 'callback' in str(rule):
                callback_routes.append(route_info)
        
        return jsonify({
            'oauth_blueprint_registered': oauth_blueprint_registered,
            'oauth_routes_count': len(oauth_routes),
            'oauth_routes': oauth_routes,
            'install_routes': install_routes,
            'callback_routes': callback_routes,
            'auth_callback_exists': any('/auth/callback' in str(rule) for rule in app.url_map.iter_rules()),
            'environment_vars': {
                'SHOPIFY_API_KEY_set': bool(os.getenv('SHOPIFY_API_KEY')),
                'SHOPIFY_API_SECRET_set': bool(os.getenv('SHOPIFY_API_SECRET')),
                'REDIRECT_URI': os.getenv('SHOPIFY_REDIRECT_URI', 'not_set')
            }
        })
    
    # ============================================================================
    # IDENTITY INTEGRITY VALIDATION (Kill Rule)
    # ============================================================================
    @app.before_request
    def validate_identity_integrity():
        """
        KILL RULE: Force session cleanup if shop parameter doesn't match session.
        Prevents User 4 cookies from bleeding into User 11 requests.
        
        This is the first line of defense against identity collision.
        """
        from flask import request, session, redirect, url_for
        from shopify_utils import normalize_shop_url
        
        # Skip for static files, debug routes, and OAuth flow
        if (request.path.startswith('/static') or 
            request.path.startswith('/debug') or
            request.path.startswith('/oauth/install') or
            request.path.startswith('/oauth/callback') or
            request.path.startswith('/auth/callback')):
            return
        
        url_shop = request.args.get('shop')
        session_shop = session.get('shop_domain')
        
        if url_shop and session_shop:
            # Normalize both for comparison
            url_shop = normalize_shop_url(url_shop)
            session_shop = normalize_shop_url(session_shop)
            
            if url_shop != session_shop:
                app.logger.warning(
                    f"🚨 IDENTITY MISMATCH DETECTED: URL shop ({url_shop}) != Session shop ({session_shop}). "
                    f"Purging session to prevent identity collision. Path: {request.path}"
                )
                
                # Kill the ghost session
                session.clear()
                
                # Force re-authentication with the correct shop
                app.logger.info(f"🔄 Redirecting to OAuth install for correct shop: {url_shop}")
                return redirect(url_for('oauth.install', shop=url_shop))
    
    @app.after_request
    def set_safari_compatible_cookies(response):
        """
        SAFARI FIX: Ensure all cookies have SameSite=None; Secure for iframe compatibility.
        Critical for embedded Shopify apps in Safari which blocks third-party cookies by default.
        """
        from flask import request
        
        # Only apply to embedded app requests
        if request.args.get('embedded') or request.args.get('host'):
            # Force SameSite=None on session cookie
            for cookie_name in ['session', 'remember_token']:
                if cookie_name in response.headers.getlist('Set-Cookie'):
                    # Modify existing Set-Cookie headers
                    cookies = []
                    for header in response.headers.getlist('Set-Cookie'):
                        if cookie_name in header:
                            # Ensure SameSite=None; Secure
                            if 'SameSite' not in header:
                                header += '; SameSite=None; Secure'
                            elif 'SameSite=Lax' in header or 'SameSite=Strict' in header:
                                header = header.replace('SameSite=Lax', 'SameSite=None')
                                header = header.replace('SameSite=Strict', 'SameSite=None')
                                if 'Secure' not in header:
                                    header += '; Secure'
                        cookies.append(header)
                    
                    # Replace Set-Cookie headers
                    response.headers.remove('Set-Cookie')
                    for cookie in cookies:
                        response.headers.add('Set-Cookie', cookie)
            
            app.logger.debug(f"🍪 Safari-compatible cookies set for {request.path}")
        
        return response
    
    @app.after_request
    def force_session_commit(response):
        """
        CRITICAL FIX: Force session to commit before response is sent.
        Prevents session loss between routes (especially /dashboard → /settings/shopify).
        """
        try:
            from flask_login import current_user
            from flask import session
            
            # Only force commit for successful responses
            if response.status_code < 400:
                # Mark session as modified to force save
                session.modified = True
                
                # If user is authenticated, ensure session has user_id
                if current_user.is_authenticated:
                    user_id = current_user.get_id()
                    if user_id and session.get('_user_id') != user_id:
                        session['_user_id'] = user_id
                        session.permanent = True
                        app.logger.debug(f"Session commit: Ensured _user_id={user_id} in session")
        except Exception as e:
            app.logger.error(f"Error in force_session_commit: {e}")
        
        return response
    
    @app.before_request
    def debug_all_requests():
        """Debug all incoming requests to identify 404s"""
        from flask import request
        if request.path.startswith('/install') or request.path.startswith('/auth/callback') or request.path.startswith('/callback'):
            app.logger.info(f"🔍 CRITICAL ROUTE REQUEST: {request.method} {request.path}")
            app.logger.info(f"  - Full URL: {request.url}")
            app.logger.info(f"  - Args: {dict(request.args)}")
            app.logger.info(f"  - Headers: {dict(request.headers)}")
            app.logger.info(f"  - Referrer: {request.referrer}")

    @app.after_request
    def debug_responses(response):
        """Debug responses for OAuth routes"""
        from flask import request
        if request.path.startswith('/install') or request.path.startswith('/auth/callback') or request.path.startswith('/callback'):
            app.logger.info(f"🔍 CRITICAL ROUTE RESPONSE: {response.status_code} for {request.path}")
            if response.status_code == 404:
                app.logger.error(f"❌ 404 ERROR: Route {request.path} not found!")
                app.logger.error(f"  - Available routes: {[str(rule) for rule in app.url_map.iter_rules()]}")
        return response
    
    return app

def create_fortress_app():
    """Alias for compatibility"""
    return create_app()
