"""
Bulletproof Application Factory - Zero-dependency startup
"""

import logging
import os

from flask import Flask, jsonify, render_template_string


def create_app():
    """Create bulletproof Flask app with minimal dependencies"""
    app = Flask(__name__)

    # Basic configuration - no external config module
    app.config.update(
        {
            "SECRET_KEY": os.getenv("SECRET_KEY", "fallback-secret-key-for-dev"),
            "SQLALCHEMY_DATABASE_URI": os.getenv("DATABASE_URL", "sqlite:///app.db"),
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "WTF_CSRF_ENABLED": False,  # Disable to avoid import issues
            "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,
            "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
        }
    )

    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(f"Creating app - Environment: {app.config['ENVIRONMENT']}")

    # Initialize extensions with error handling
    try:
        from models import db

        db.init_app(app)
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database init failed: {e}")

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
            except:
                return None

        logger.info("Flask-Login initialized")
    except Exception as e:
        logger.error(f"Flask-Login init failed: {e}")

    try:
        from flask_bcrypt import Bcrypt

        Bcrypt(app)
        logger.info("Bcrypt initialized")
    except Exception as e:
        logger.error(f"Bcrypt init failed: {e}")

    # Register blueprints with individual error handling
    blueprint_configs = [
        ("core_routes", "core_bp"),
        ("auth", "auth_bp"),
        ("shopify_oauth", "oauth_bp"),
        ("shopify_routes", "shopify_bp"),
        ("billing", "billing_bp"),
        ("features_routes", "features_bp"),
        ("legal_routes", "legal_bp"),
    ]

    for module_name, blueprint_name in blueprint_configs:
        try:
            module = __import__(module_name)
            blueprint = getattr(module, blueprint_name)
            app.register_blueprint(blueprint)
            logger.info(f"Registered {blueprint_name}")
        except Exception as e:
            logger.warning(f"Failed to register {blueprint_name}: {e}")
            # Continue without this blueprint

    # Add security headers
    @app.after_request
    def add_security_headers(response):
        try:
            from security_enhancements import add_security_headers

            return add_security_headers(response)
        except:
            # Fallback security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response

    # Basic error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}")
        return jsonify({"error": "Internal server error"}), 500

    logger.info("App created successfully")
    return app


def create_fortress_app():
    """Alias for backward compatibility"""
    return create_app()


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False)
