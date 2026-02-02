#!/usr/bin/env python3
"""
Main entry point for MissionControl Shopify App.
WSGI servers should use: gunicorn main:app
"""

import os
import sys
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent.absolute()
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# OPTIMIZATION: Set environment flag to skip heavy startup operations
os.environ.setdefault("SKIP_STARTUP_MIGRATIONS", "true")

# Try to import app_factory, fallback to basic Flask app if not available
try:
    from app_factory import create_app

    # For WSGI servers (Gunicorn, uWSGI, etc.)
    app = create_app()
except ImportError as e:
    # Fallback: Create basic Flask app if app_factory is missing
    import logging

    from flask import Flask, jsonify
    from flask_login import LoginManager

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        try:
            from models import User

            return User.query.get(int(user_id))
        except Exception as e:
            logger.error(f"Error loading user {user_id}: {e}")
            return None

    # Health check endpoint
    @app.route("/health")
    def health_check():
        """Health check endpoint for Render deployment monitoring"""
        try:
            return jsonify(
                {"status": "healthy", "service": "employeesuite", "version": "1.0.0"}
            ), 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({"status": "unhealthy", "error": str(e)}), 500

    # Initialize database
    def ensure_db_initialized():
        """Ensure database is initialized"""
        try:
            from models import ShopifyStore, User, db

            db.init_app(app)
            with app.app_context():
                db.create_all()
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    # Register blueprints
    try:
        from auth import auth_bp
        from shopify_oauth import oauth_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(oauth_bp)

        logger.info("Blueprints registered successfully")
    except Exception as e:
        logger.error(f"Failed to register blueprints: {e}")

    # Dashboard route
    @app.route("/dashboard")
    def dashboard():
        """Main dashboard route"""
        return jsonify({"message": "Dashboard - under construction"})

    @app.route("/")
    def index():
        """Root route"""
        return jsonify({"message": "Employee Suite API", "status": "running"})

    # Initialize database on app creation
    try:
        ensure_db_initialized()
    except Exception as e:
        logger.error(f"Database initialization failed during app creation: {e}")

    logger.warning(f"Using fallback Flask app due to import error: {e}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug_mode, threaded=True)
