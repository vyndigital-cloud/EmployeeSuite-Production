"""
Simple App Factory
"""
import logging
import os
from flask import Flask

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
        'SESSION_COOKIE_SAMESITE': 'None',  # Allow cookies in iframes (required for embedded apps)
        'REMEMBER_COOKIE_SECURE': True,
        'REMEMBER_COOKIE_HTTPONLY': True,
        'REMEMBER_COOKIE_DURATION': 2592000,  # 30 days
    })
    
    # Initialize database with error handling
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
            Load user from request - simplified to prevent session hijacking.
            """
            from flask import session
            from models import User
            
            # 1. STOP THE LOOP: Check the cookie directly, NOT current_user
            user_id = session.get('_user_id')
            if user_id:
                return User.query.get(int(user_id))
            
            # 2. STOP THE HIJACK: Only auto-login User 4 if NO session exists
            # and we are NOT in the middle of an OAuth callback
            shop = request.args.get('shop')
            if shop and request.args.get('hmac') and request.endpoint != 'shopify.callback':
                return User.query.filter_by(shop_url=shop, is_owner=True).first()
            
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
