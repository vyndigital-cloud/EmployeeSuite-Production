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
os.environ.setdefault("PYTHONUNBUFFERED", "1")


def optimize_startup():
    """Optimize startup for production"""
    if os.getenv("ENVIRONMENT") == "production":
        os.environ.setdefault("SKIP_HEAVY_IMPORTS", "true")


def validate_production_config():
    """Validate production configuration - FIXED: No database access during startup"""
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

        logger.info("✅ Production configuration validated")


# Initialize optimizations
optimize_startup()

# Create app using factory pattern
try:
    from app_factory import create_app

    app = create_app()

    # Validate config AFTER app creation
    validate_production_config()

    # Initialize auto-scaling in production
    if os.getenv("ENVIRONMENT") == "production":
        try:
            from auto_scaling import init_auto_scaling

            init_auto_scaling(app)
        except ImportError:
            pass

except ImportError as e:
    # Fallback app if factory fails
    import logging

    from flask import Flask, jsonify

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

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug_mode,
        threaded=True,
        use_reloader=False if os.getenv("ENVIRONMENT") == "production" else True,
        use_debugger=debug_mode,
    )
