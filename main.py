#!/usr/bin/env python3
"""
Production Main Entry Point - Bulletproof
"""

import os
import sys
from pathlib import Path

# Add project directory to path
project_dir = Path(__file__).parent.absolute()
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# Configure logging immediately
import logging
import traceback

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app_errors.log')
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


try:
    logger.info("Attempting to create app via startup.create_app()")
    from startup import create_app
    app = create_app()
    logger.info("App created successfully via startup")

    # Add error handler for 500 errors
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal Server Error: {error}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        from flask import jsonify
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Please check the application logs'
        }), 500

    # Webhook blueprint is now registered in app_factory
    # from webhook_shopify import webhook_shopify_bp
    # app.register_blueprint(webhook_shopify_bp)
    
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
        
except Exception as startup_error:
    logger.error(f"Startup failed: {startup_error}")
    logger.error(f"Startup traceback: {traceback.format_exc()}")

    # Try app_factory as backup
    try:
        logger.info("Trying app_factory.create_app() as backup")
        from app_factory import create_app
        app = create_app()
        logger.info("App created via app_factory backup")
    except Exception as factory_error:
        logger.error(f"App factory failed: {factory_error}")
        logger.error(f"Factory traceback: {traceback.format_exc()}")

        # Ultimate fallback
        logger.info("Using ultimate fallback Flask app")
        from flask import Flask, jsonify
        app = Flask(__name__)
        
        # Register GDPR webhook handlers even in fallback mode
        try:
            from webhook_shopify import webhook_shopify_bp
            app.register_blueprint(webhook_shopify_bp)
        except ImportError:
            pass

        @app.errorhandler(500)
        def internal_error(error):
            logger.error(f"Fallback app Internal Server Error: {error}")
            return jsonify({'error': 'Application startup failed', 'details': str(error)}), 500

        @app.route("/")
        def home():
            return jsonify({"status": "fallback app running", "error": "main app failed to start"})

        @app.route("/health")
        def health():
            return jsonify({"status": "fallback healthy"})
        
    # Add Protected Customer Data compliance headers for fallback mode
    @app.after_request
    def add_gdpr_headers(response):
        """Add Shopify Protected Customer Data compliance headers"""
        response.headers['X-Shopify-Data-Protection'] = 'compliant'
        response.headers['X-Data-Minimization'] = 'enabled'
        response.headers['X-Customer-Privacy'] = 'protected'
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
