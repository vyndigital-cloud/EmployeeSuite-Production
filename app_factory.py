"""
Application Factory for MissionControl Shopify App
Resolves circular import issues and provides clean application initialization
"""

import logging
import os
from typing import Optional

from flask import Flask

from config import get_config
from csrf_protection import init_csrf_protection
from logging_config import setup_logging
from models import db, init_db


def create_app(config_name: Optional[str] = None) -> Flask:
    """
    Application factory function

    Args:
        config_name: Configuration name (development, production, testing)

    Returns:
        Configured Flask application
    """
    # Create Flask app instance
    app = Flask(__name__)

    # Load configuration
    if config_name:
        os.environ["ENVIRONMENT"] = config_name

    config = get_config()

    # Configure Flask app
    app.config.from_object(config)

    # Additional Flask configuration
    app.config.update(
        {
            "SQLALCHEMY_DATABASE_URI": config.SQLALCHEMY_DATABASE_URI,
            "SQLALCHEMY_TRACK_MODIFICATIONS": config.SQLALCHEMY_TRACK_MODIFICATIONS,
            "SQLALCHEMY_ENGINE_OPTIONS": config.SQLALCHEMY_ENGINE_OPTIONS,
            "SECRET_KEY": config.SECRET_KEY,
            "WTF_CSRF_ENABLED": config.WTF_CSRF_ENABLED,
            "WTF_CSRF_TIME_LIMIT": config.WTF_CSRF_TIME_LIMIT,
            "MAX_CONTENT_LENGTH": config.MAX_CONTENT_LENGTH,
        }
    )

    # Setup logging first
    logger = setup_logging(app)
    logger.info(f"Creating MissionControl app - Environment: {config.ENVIRONMENT}")

    # Initialize extensions
    init_extensions(app)

    # Register blueprints (avoid circular imports by importing here)
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Register CLI commands
    register_cli_commands(app)

    # Setup request/response hooks
    setup_hooks(app)

    # Initialize database - OPTIMIZED for production
    with app.app_context():
        # Skip heavy operations in production to prevent timeouts
        if (
            config.ENVIRONMENT == "production"
            and os.getenv("SKIP_STARTUP_MIGRATIONS") == "true"
        ):
            logger.info("Skipping database migrations in production for fast startup")
        else:
            init_db(app)

    logger.info("MissionControl application created successfully")
    return app


def init_extensions(app: Flask) -> None:
    """Initialize Flask extensions"""
    logger = logging.getLogger("missioncontrol.factory")

    try:
        # Initialize database
        db.init_app(app)
        logger.info("Database extension initialized")

        # Initialize CSRF protection - TEMPORARILY DISABLED due to Flask-WTF compatibility
        # init_csrf_protection(app)
        logger.info("CSRF protection temporarily disabled for deployment")

        # Initialize Flask-Login
        from flask_login import LoginManager

        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = "auth.login"
        login_manager.login_message = "Please log in to access this page."
        login_manager.login_message_category = "info"

        # User loader function
        @login_manager.user_loader
        def load_user(user_id):
            from models import User

            try:
                return User.query.get(int(user_id))
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass
                return None

        # Shopify-specific unauthorized handler
        @login_manager.unauthorized_handler
        def unauthorized():
            from flask import has_request_context, redirect, request, session, url_for

            from utils import safe_redirect

            if not has_request_context():
                return redirect("/install")

            shop = (
                request.args.get("shop")
                or session.get("shop")
                or session.get("current_shop")
            )
            host = request.args.get("host")

            if not shop:
                referer = request.headers.get("Referer", "")
                if "myshopify.com" in referer or "admin.shopify.com" in referer:
                    try:
                        from urllib.parse import urlparse

                        parsed = urlparse(referer)
                        if ".myshopify.com" in parsed.netloc:
                            shop = parsed.netloc
                        elif "/store/" in parsed.path:
                            shop_name = parsed.path.split("/store/")[1].split("/")[0]
                            shop = f"{shop_name}.myshopify.com"
                    except Exception:
                        pass

            if shop:
                install_url = (
                    url_for("oauth.install", shop=shop, host=host)
                    if host
                    else url_for("oauth.install", shop=shop)
                )
                return safe_redirect(install_url, shop=shop, host=host)

            return redirect("/install")

        logger.info("Flask-Login initialized")

        # Initialize Flask-Bcrypt
        from flask_bcrypt import Bcrypt

        bcrypt = Bcrypt(app)
        logger.info("Flask-Bcrypt initialized")

        # Initialize rate limiter
        from rate_limiter import init_limiter

        init_limiter(app)
        logger.info("Rate limiter initialized")

        # DISABLED: Sentry initialization causing startup delays
        # Initialize Sentry (if configured) - TEMPORARILY DISABLED
        if False and app.config.get("SENTRY_DSN"):  # Force disable
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=app.config["SENTRY_DSN"],
                integrations=[
                    FlaskIntegration(),
                    SqlalchemyIntegration(),
                ],
                traces_sample_rate=0.1,
                environment=app.config.get("ENVIRONMENT", "development"),
            )
            logger.info("Sentry error tracking initialized")
        else:
            logger.info("Sentry disabled to prevent startup delays")

    except Exception as e:
        logger.error(f"Extension initialization failed: {e}")
        raise


def register_blueprints(app: Flask) -> None:
    """Register application blueprints"""
    logger = logging.getLogger("missioncontrol.factory")

    try:
        # Import core blueprints (these exist)
        from auth import auth_bp
        from billing import billing_bp
        from core_routes import core_bp
        from shopify_oauth import oauth_bp
        from shopify_routes import shopify_bp

        # Register core blueprints first
        app.register_blueprint(core_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(oauth_bp)
        app.register_blueprint(shopify_bp)
        app.register_blueprint(billing_bp)

        logger.info("Core blueprints registered successfully")

        # Try to import optional blueprints (may not exist)
        optional_blueprints = [
            ("admin_routes", "admin_bp", None),
            ("faq_routes", "faq_bp", None),
            ("gdpr_compliance", "gdpr_bp", None),
            ("legal_routes", "legal_bp", "/legal"),
            ("webhook_shopify", "webhook_shopify_bp", None),
            ("webhook_stripe", "webhook_bp", None),
        ]

        for module_name, blueprint_name, url_prefix in optional_blueprints:
            try:
                module = __import__(module_name)
                blueprint = getattr(module, blueprint_name)
                if url_prefix:
                    app.register_blueprint(blueprint, url_prefix=url_prefix)
                else:
                    app.register_blueprint(blueprint)
                logger.info(f"Optional blueprint {blueprint_name} registered")
            except ImportError:
                logger.info(f"Optional blueprint {module_name} not found, skipping")
            except AttributeError:
                logger.warning(f"Blueprint {blueprint_name} not found in {module_name}")

    except ImportError as e:
        logger.error(f"Failed to register core blueprints: {e}")
        raise  # Core blueprints are required


def register_error_handlers(app: Flask) -> None:
    """Register error handlers"""
    from flask import jsonify, render_template_string, request

    @app.errorhandler(400)
    def bad_request(error):
        if request.is_json:
            return jsonify(
                {
                    "error": "Bad Request",
                    "message": "The request could not be understood by the server",
                    "code": 400,
                }
            ), 400
        return render_template_string("""
            <h1>400 - Bad Request</h1>
            <p>The request could not be understood by the server.</p>
            <a href="/">Go Home</a>
        """), 400

    @app.errorhandler(401)
    def unauthorized(error):
        if request.is_json:
            return jsonify(
                {
                    "error": "Unauthorized",
                    "message": "Authentication is required",
                    "code": 401,
                }
            ), 401
        return render_template_string("""
            <h1>401 - Unauthorized</h1>
            <p>Authentication is required to access this resource.</p>
            <a href="/auth/login">Login</a>
        """), 401

    @app.errorhandler(403)
    def forbidden(error):
        if request.is_json:
            return jsonify(
                {
                    "error": "Forbidden",
                    "message": "You do not have permission to access this resource",
                    "code": 403,
                }
            ), 403
        return render_template_string("""
            <h1>403 - Forbidden</h1>
            <p>You do not have permission to access this resource.</p>
            <a href="/">Go Home</a>
        """), 403

    @app.errorhandler(404)
    def not_found(error):
        if request.is_json:
            return jsonify(
                {
                    "error": "Not Found",
                    "message": "The requested resource was not found",
                    "code": 404,
                }
            ), 404
        return render_template_string("""
            <h1>404 - Page Not Found</h1>
            <p>The page you are looking for does not exist.</p>
            <a href="/">Go Home</a>
        """), 404

    @app.errorhandler(500)
    def internal_error(error):
        # Log the error
        logger = logging.getLogger("missioncontrol.errors")
        logger.error(f"Internal server error: {error}", exc_info=True)

        if request.is_json:
            return jsonify(
                {
                    "error": "Internal Server Error",
                    "message": "An internal server error occurred",
                    "code": 500,
                }
            ), 500
        return render_template_string("""
            <h1>500 - Internal Server Error</h1>
            <p>An internal server error occurred. Please try again later.</p>
            <a href="/">Go Home</a>
        """), 500


def register_cli_commands(app: Flask) -> None:
    """Register CLI commands"""
    import click

    @app.cli.command("init-db")
    def init_db_command():
        """Initialize the database"""
        try:
            init_db(app)
            click.echo("Database initialized successfully.")
        except Exception as e:
            click.echo(f"Database initialization failed: {e}", err=True)

    @app.cli.command("create-user")
    @click.argument("email")
    @click.argument("password")
    def create_user_command(email, password):
        """Create a new user"""
        try:
            from models import create_user

            user = create_user(email, password)
            click.echo(f"User created successfully: {user.email}")
        except Exception as e:
            click.echo(f"User creation failed: {e}", err=True)

    @app.cli.command("generate-key")
    def generate_key_command():
        """Generate a new encryption key"""
        from data_encryption import generate_encryption_key

        key = generate_encryption_key()
        click.echo(f"Generated encryption key: {key}")
        click.echo("Add this to your environment: ENCRYPTION_KEY=" + key)


def setup_hooks(app: Flask) -> None:
    """Setup request/response hooks"""
    from flask import g, jsonify, request

    from logging_config import PerformanceLogger

    @app.before_request
    def before_request():
        """Setup request context with security validation"""
        logger = logging.getLogger("missioncontrol.config")
        logger.info(f"Making request to: {request.path}, Method: {request.method}")

        # Skip validation for static files and health checks
        if request.endpoint in ("static", "core.favicon", "core.apple_touch_icon"):
            return

        # Start performance monitoring
        g.start_time = None
        if not request.endpoint or request.endpoint not in ["static", "core.favicon"]:
            g.perf_logger = PerformanceLogger(
                f"{request.method} {request.endpoint or 'unknown'}"
            )
            g.perf_logger.__enter__()

        # Request size validation for POST/PUT
        if request.method in ("POST", "PUT") and request.content_length:
            max_size = app.config.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
            if request.content_length > max_size:
                return jsonify({"error": "Request too large"}), 413

    @app.after_request
    def after_request(response):
        """Process response - security headers and compression"""
        try:
            from security_enhancements import add_security_headers

            response = add_security_headers(response)

            # Try response compression
            try:
                from performance import compress_response

                response = compress_response(response)
            except Exception:
                pass

            # End performance monitoring
            if hasattr(g, "perf_logger"):
                g.perf_logger.__exit__(None, None, None)

            # Keep-Alive for webhook endpoints (Shopify requirement)
            if request.path.startswith("/webhooks/") or request.path.startswith(
                "/webhook/"
            ):
                response.headers["Connection"] = "keep-alive"
                response.headers["Keep-Alive"] = "timeout=5, max=1000"

        except Exception as e:
            logging.getLogger("missioncontrol.errors").error(
                f"Error in after_request handler: {e}", exc_info=True
            )

        return response

    @app.teardown_appcontext
    def close_db(error):
        """Close database session after each request"""
        try:
            if db.session.is_active:
                db.session.remove()
        except Exception:
            pass


def create_test_app() -> Flask:
    """Create app for testing"""
    return create_app("testing")


def create_dev_app() -> Flask:
    """Create app for development"""
    return create_app("development")


def create_prod_app() -> Flask:
    """Create app for production"""
    return create_app("production")


if __name__ == "__main__":
    # Development server
    dev_app = create_dev_app()
    dev_app.run(host="0.0.0.0", port=5000, debug=True)
