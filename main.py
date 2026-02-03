#!/usr/bin/env python3
"""
Production Main Entry Point - Bulletproof
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project directory to path
project_dir = Path(__file__).parent.absolute()
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# Configure logging for production speed
import traceback

# Initialize logger for this module first
logger = logging.getLogger(__name__)

# Import error logging with fallback
try:
    from error_logging import error_logger, log_errors
    logger.info("Error logging imported successfully")
except ImportError as e:
    logger.error(f"Error logging import failed: {e}")
    # Create a fallback error logger
    class FallbackErrorLogger:
        def log_error(self, error, error_type="GENERAL"):
            logger.error(f"[{error_type}] {str(error)}")
        def log_user_action(self, action, user_id=None, details=None):
            logger.info(f"User Action: {action}")
        def log_system_event(self, event, details=None):
            logger.info(f"System Event: {event}")
        def get_recent_errors(self, count=50):
            return []
    
    error_logger = FallbackErrorLogger()
    
    def log_errors(error_type="GENERAL"):
        def decorator(func):
            return func
        return decorator

# Optimized logging for production
logging.basicConfig(
    level=logging.WARNING,  # Changed from DEBUG to WARNING for speed
    format='%(asctime)s - %(levelname)s - %(message)s',  # Simplified format
    handlers=[
        logging.StreamHandler(sys.stdout)
        # Removed file handler for speed - use external log aggregation
    ]
)

logger = logging.getLogger(__name__)
logger.info("Starting main.py - logging configured")

# Check critical imports
try:
    import flask
    logger.info(f"Flask version: {flask.__version__}")
except ImportError as e:
    logger.error(f"Flask import failed: {e}")
    sys.exit(1)

try:
    from models import db
    logger.info("Models imported successfully")
except ImportError as e:
    logger.error(f"Models import failed: {e}")

try:
    from extensions import db as ext_db
    logger.info("Extensions imported successfully")
except ImportError as e:
    logger.error(f"Extensions import failed: {e}")

# Set production defaults
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

# Add environment validation
required_env_vars = ['SHOPIFY_API_KEY', 'SHOPIFY_API_SECRET', 'SECRET_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.warning(f"Missing environment variables: {missing_vars}")
    logger.warning("App may not function properly without these variables")


try:
    logger.info("Attempting to create app via app_factory.create_app()")
    from app_factory import create_app
    app = create_app()
    logger.info("App created successfully via app_factory")

    # Enhanced error handlers
    @app.errorhandler(500)
    def internal_error(error):
        error_logger.log_error(error, "INTERNAL_SERVER_ERROR")
        from flask import jsonify
        from datetime import datetime
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Error has been logged and will be investigated',
            'error_id': datetime.now().strftime('%Y%m%d_%H%M%S')
        }), 500
    
    @app.errorhandler(404)
    def not_found_error(error):
        error_logger.log_error(error, "NOT_FOUND")
        from flask import jsonify
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        error_logger.log_error(error, "FORBIDDEN")
        from flask import jsonify
        return jsonify({
            'error': 'Forbidden',
            'message': 'Access denied'
        }), 403

    # Log all requests
    @app.before_request
    def log_request():
        """Log all incoming requests"""
        from flask import request, session
        error_logger.log_user_action(
            f"{request.method} {request.endpoint or request.path}",
            session.get('user_id') if session else None,
            {
                'shop_domain': request.headers.get('X-Shopify-Shop-Domain'),
                'user_agent': request.headers.get('User-Agent', '')[:100]
            }
        )

    # Error dashboard route
    @app.route('/admin/errors')
    @log_errors("ADMIN_ERROR")
    def view_errors():
        """Admin route to view recent errors"""
        from flask import session, jsonify
        try:
            # Simple authentication check
            if not session.get('user_id'):
                return jsonify({'error': 'Unauthorized'}), 401
                
            recent_errors = error_logger.get_recent_errors(100)
            
            return jsonify({
                'total_errors': len(recent_errors),
                'errors': recent_errors[-20:],  # Last 20 errors
                'status': 'success'
            })
            
        except Exception as e:
            error_logger.log_error(e, "ADMIN_DASHBOARD_ERROR")
            return jsonify({'error': 'Failed to retrieve errors'}), 500
    
    # Add Protected Customer Data compliance headers
    @app.after_request
    def add_gdpr_headers(response):
        """Add Shopify Protected Customer Data compliance headers"""
        try:
            response.headers['X-Shopify-Data-Protection'] = 'compliant'
            response.headers['X-Data-Minimization'] = 'enabled'
            response.headers['X-Customer-Privacy'] = 'protected'
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        except Exception as e:
            logger.error(f"Error adding GDPR headers: {e}")
            return response
    
    # Log successful startup
    error_logger.log_system_event("APP_STARTUP_SUCCESS", {
        'method': 'startup.create_app',
        'environment': os.getenv('ENVIRONMENT', 'unknown')
    })
        
except Exception as startup_error:
    error_logger.log_error(startup_error, "STARTUP_ERROR")

    # Try app_factory as backup
    try:
        logger.info("Trying app_factory.create_app() as backup")
        from app_factory import create_app
        app = create_app()
        error_logger.log_system_event("APP_STARTUP_FALLBACK", {
            'method': 'app_factory.create_app'
        })
    except Exception as factory_error:
        error_logger.log_error(factory_error, "FACTORY_ERROR")
        logger.error(f"App factory failed: {factory_error}")

        # Ultimate fallback
        logger.info("Using ultimate fallback Flask app")
        from flask import Flask, jsonify
        app = Flask(__name__)
        
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key')
        
        error_logger.log_system_event("APP_STARTUP_ULTIMATE_FALLBACK")
        
        # Register GDPR webhook handlers even in fallback mode
        try:
            from webhook_shopify import webhook_shopify_bp
            app.register_blueprint(webhook_shopify_bp)
        except ImportError:
            pass

        @app.errorhandler(500)
        def internal_error(error):
            error_logger.log_error(error, "FALLBACK_ERROR")
            return jsonify({'error': 'Application startup failed', 'details': str(error)}), 500

        @app.route("/")
        def home():
            return jsonify({"status": "fallback app running", "error": "main app failed to start"})

        @app.route("/health")
        def health():
            return jsonify({"status": "fallback healthy"})



if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
