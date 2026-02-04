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
        ('shopify_oauth', 'oauth_bp'),
        ('shopify_routes', 'shopify_bp'),
        ('billing', 'billing_bp'),
        ('features_pages', 'features_pages_bp'),
        ('features_routes', 'features_bp'),
        ('legal_routes', 'legal_bp'),
        ('gdpr_compliance', 'gdpr_bp'),
        ('webhook_shopify', 'webhook_shopify_bp'),
        ('faq_routes', 'faq_bp'),
        ('enhanced_features', 'enhanced_bp'),
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
        except (ImportError, AttributeError) as e:
            failed_blueprints.append(f"{blueprint_name}: {str(e)}")
            app.logger.warning(f"❌ Could not register blueprint {blueprint_name} from {module_name}: {e}")
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
    
    return app

def create_fortress_app():
    """Alias for compatibility"""
    return create_app()
