#!/usr/bin/env python3
"""
Production-ready startup script for MissionControl Shopify App
Handles proper application initialization, environment setup, and graceful shutdown
"""

import logging
import os
import signal
import sys
from pathlib import Path

# Ensure project directory is in path
project_dir = Path(__file__).parent.absolute()
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# Configure basic logging before any other imports
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("missioncontrol.startup")


def setup_environment():
    """Setup environment variables and validate configuration"""
    logger.info("Setting up environment...")

    # Set default environment if not specified
    if not os.getenv("ENVIRONMENT"):
        os.environ["ENVIRONMENT"] = "development"

    # Validate critical environment variables for production
    if os.getenv("ENVIRONMENT") == "production":
        required_vars = [
            "SECRET_KEY",
            "DATABASE_URL",
            "SHOPIFY_API_KEY",
            "SHOPIFY_API_SECRET",
            "ENCRYPTION_KEY",
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            sys.exit(1)

    # Set threading options to prevent segfaults
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OMP_NUM_THREADS"] = "1"

    logger.info(f"Environment: {os.getenv('ENVIRONMENT')}")


def handle_shutdown_signal(signum, frame):
    """Handle graceful shutdown"""
    logger.info(f"Received shutdown signal {signum}")
    logger.info("Shutting down gracefully...")
    sys.exit(0)


def check_dependencies():
    """Check if all required dependencies are available"""
    logger.info("Checking dependencies...")

    required_modules = [
        "flask",
        "sqlalchemy",
        "psycopg2",
        "cryptography",
        "flask_login",
        "flask_wtf",
        "sentry_sdk",
    ]

    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    if missing_modules:
        logger.error(f"Missing required modules: {missing_modules}")
        logger.error("Run: pip install -r requirements.txt")
        sys.exit(1)

    logger.info("All dependencies available")


def create_application():
    """Create and configure Flask application"""
    logger.info("Creating Flask application...")

    try:
        from app_factory import create_app

        app = create_app()
        logger.info("Application created successfully")
        return app

    except ImportError as e:
        logger.error(f"Could not import application factory: {e}")
        logger.info("Falling back to legacy app.py...")

        try:
            import app as legacy_app

            if hasattr(legacy_app, "app"):
                return legacy_app.app
            else:
                logger.error("Legacy app.py does not have 'app' object")
                sys.exit(1)
        except ImportError as e2:
            logger.error(f"Could not import legacy app: {e2}")
            sys.exit(1)


def run_development_server(app):
    """Run development server"""
    logger.info("Starting development server...")

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "False").lower() == "true"

    logger.info(f"Server running at http://{host}:{port}")
    logger.info(f"Debug mode: {debug}")

    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True,
            use_reloader=False,  # Disable reloader to prevent issues
        )
    except KeyboardInterrupt:
        logger.info("Development server stopped by user")
    except Exception as e:
        logger.error(f"Development server error: {e}")
        sys.exit(1)


def run_production_server(app):
    """Instructions for production deployment"""
    logger.info("Production mode detected")
    logger.info("For production deployment, use a WSGI server like Gunicorn:")

    port = os.getenv("PORT", 5000)
    workers = os.getenv("WEB_CONCURRENCY", 4)

    print(f"""
Production Deployment Commands:

1. Using Gunicorn (recommended):
   gunicorn -w {workers} -b 0.0.0.0:{port} --timeout 120 run:app

2. Using uWSGI:
   uwsgi --http 0.0.0.0:{port} --module run:app --processes {workers}

3. Using Waitress:
   waitress-serve --host=0.0.0.0 --port={port} run:app

Environment: {os.getenv("ENVIRONMENT")}
Workers: {workers}
Port: {port}
""")


def health_check():
    """Perform basic health checks"""
    logger.info("Performing health checks...")

    # Check database connectivity
    try:
        from models import db

        # This will be tested when app starts
        logger.info("Database module loaded")
    except Exception as e:
        logger.error(f"Database connectivity issue: {e}")
        return False

    # Check configuration
    try:
        from config import get_config

        config = get_config()
        logger.info(f"Configuration loaded: {config.ENVIRONMENT}")
    except Exception as e:
        logger.error(f"Configuration issue: {e}")
        return False

    return True


def main():
    """Main application entry point"""
    logger.info("=" * 60)
    logger.info("🚀 Starting MissionControl Shopify App")
    logger.info("=" * 60)

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)

    try:
        # Setup environment
        setup_environment()

        # Check dependencies
        check_dependencies()

        # Health checks
        if not health_check():
            logger.error("Health checks failed")
            sys.exit(1)

        # Create application
        app = create_application()

        # Determine how to run based on environment
        environment = os.getenv("ENVIRONMENT", "development")

        if environment == "development":
            run_development_server(app)
        else:
            run_production_server(app)

    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Application shutdown complete")


# For WSGI servers
try:
    app = create_application()
except Exception as e:
    logger.error(f"Could not create WSGI app: {e}")
    app = None

if __name__ == "__main__":
    main()
