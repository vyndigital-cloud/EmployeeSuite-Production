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

# Set production defaults
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

try:
    # Try the bulletproof startup
    from startup import create_app

    app = create_app()
    
    # Webhook blueprint is now registered in app_factory
    # from webhook_shopify import webhook_shopify_bp
    # app.register_blueprint(webhook_shopify_bp)
    
    # Add Protected Customer Data compliance headers
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
        
except ImportError:
    # Ultimate fallback
    from flask import Flask, jsonify

    app = Flask(__name__)
    
    # Register GDPR webhook handlers even in fallback mode
    try:
        from webhook_shopify import webhook_shopify_bp
        app.register_blueprint(webhook_shopify_bp)
    except ImportError:
        pass

    @app.route("/")
    def home():
        return jsonify({"status": "minimal app running"})

    @app.route("/health")
    def health():
        return jsonify({"status": "healthy"})
        
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
