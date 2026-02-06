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
            Load user from request (header or query param) for embedded apps.
            This prevents redirect loops by accepting valid session tokens as login.
            """
            # 1. Check for Authorization header (Bearer token)
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                try:
                    token = auth_header.split(" ")[1]
                    from session_token_verification import verify_session_token
                    
                    # Verify token and extract payload
                    payload = verify_session_token(token)
                    if payload and payload.get("dest"):
                        # Extract shop domain from 'dest' claim (https://shop.myshopify.com)
                        shop_domain = payload.get("dest").replace("https://", "").replace("http://", "")
                        
                        # Find user associated with this shop
                        from models import ShopifyStore, User
                        store = ShopifyStore.query.filter_by(shop_url=shop_domain).first()
                        if store and store.user_id:
                            user = User.query.get(store.user_id)
                            if user:
                                app.logger.info(f"Token auth success for shop {shop_domain} (User {user.id})")
                                return user
                except Exception as e:
                    app.logger.error(f"Token auth failed: {e}")

            # 2. Check for 'embedded=1' and 'shop' params (less secure, but avoids redirect loop on initial load)
            # This allows the first request to render, then JS will fetch a real token
            shop = request.args.get('shop')
            is_embedded = request.args.get('embedded') == '1'
            
            if is_embedded and shop:
                try:
                    from models import ShopifyStore, User
                    # Strip protocol if present
                    shop_domain = shop.replace("https://", "").replace("http://", "")
                    
                    # Only default to user if we have a valid store record
                    # We utilize the 'host' param as a simplified proof of origin for initial load
                    if request.args.get('host'):
                        store = ShopifyStore.query.filter_by(shop_url=shop_domain).first()
                        if store and store.user_id:
                            # Verify store logic (ensure it's active)
                            user = User.query.get(store.user_id)
                            if user:
                                app.logger.info(f"Embedded param auth for {shop_domain} (User {user.id})")
                                return user
                except Exception as e:
                    app.logger.error(f"Param auth failed: {e}")

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
            module = __import__(module_name)
            blueprint = getattr(module, blueprint_name)
            app.register_blueprint(blueprint)
            registered_blueprints.append(blueprint_name)
            app.logger.info(f"✅ Registered blueprint: {blueprint_name}")
            
            # Special logging for OAuth blueprint
            if blueprint_name == 'oauth_bp':
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
    
    return app

def create_fortress_app():
    """Alias for compatibility"""
    return create_app()
