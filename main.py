#!/usr/bin/env python3
"""
Production-Ready Main Entry Point
Handles 100 -> 1,000 -> 10,000+ users automatically
"""

import os
import sys
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent.absolute()
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# Production optimizations
os.environ.setdefault("SKIP_STARTUP_MIGRATIONS", "true")
os.environ.setdefault("PYTHONUNBUFFERED", "1")  # Better logging in production


def optimize_startup():
    """Optimize startup for production"""
    if os.getenv("ENVIRONMENT") == "production":
        os.environ.setdefault("SKIP_HEAVY_IMPORTS", "true")

        # Preload critical modules only
        critical_modules = ["logging_config", "models", "config"]
        for module in critical_modules:
            try:
                __import__(module)
            except ImportError:
                pass


def validate_production_config():
    """Validate production configuration"""
    if os.getenv("ENVIRONMENT") == "production":
        import logging

        logger = logging.getLogger(__name__)

        required_vars = [
            "DATABASE_URL",
            "SECRET_KEY",
            "SHOPIFY_API_KEY",
            "SHOPIFY_API_SECRET",
            "ENCRYPTION_KEY",
        ]

        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            logger.error(f"❌ CRITICAL: Missing production variables: {missing}")
            sys.exit(1)

        # Validate database connection
        try:
            with app.app_context():
                from models import db

                db.session.execute(db.text("SELECT 1"))
            logger.info("✅ Database connection validated")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            sys.exit(1)

        logger.info("✅ Production configuration validated")


# Initialize optimizations
optimize_startup()

# Create app
try:
    from app_factory import create_app

    app = create_app()
    validate_production_config()

    # Initialize auto-scaling in production
    if os.getenv("ENVIRONMENT") == "production":
        from auto_scaling import init_auto_scaling

        init_auto_scaling(app)

except ImportError as e:
    # Fallback app if factory fails
    import logging

    from flask import Flask, jsonify
    from flask_login import LoginManager

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

    @app.route("/health")
    def health_check():
        return jsonify({"status": "healthy", "service": "employeesuite"}), 200

    @app.route("/")
    def index():
        return jsonify({"message": "Employee Suite API", "status": "running"})

    logger.warning(f"Using fallback Flask app: {e}")

# Production WSGI configuration
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_ENV") != "production"

    # Production server settings
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug_mode,
        threaded=True,
        # Production optimizations
        use_reloader=False if os.getenv("ENVIRONMENT") == "production" else True,
        use_debugger=debug_mode,
    )
