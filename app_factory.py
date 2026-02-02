"""
Production-Grade Fortress Application Factory
Implements resilience, self-correction, and fail-fast principles
"""

import logging
import os
import sys
from typing import Optional

from flask import Flask, jsonify

# Import fortress components with fallbacks
try:
    from config import ConfigValidationError, get_config
except ImportError:
    # Fallback configuration
    def get_config():
        return {
            "SECRET_KEY": os.getenv("SECRET_KEY", "dev-secret-key"),
            "SHOPIFY_API_KEY": os.getenv("SHOPIFY_API_KEY", ""),
            "SHOPIFY_API_SECRET": os.getenv("SHOPIFY_API_SECRET", ""),
            "DATABASE_URL": os.getenv("DATABASE_URL", "sqlite:///app.db"),
            "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
            "SQLALCHEMY_DATABASE_URI": os.getenv("DATABASE_URL", "sqlite:///app.db"),
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "WTF_CSRF_ENABLED": True,
            "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,
        }

    class ConfigValidationError(Exception):
        pass


# Fix the fortress components imports:
try:
    from core.circuit_breaker import database_breaker, shopify_breaker
    from core.cleanup import init_cleanup_middleware
    from core.degradation import service_status

    FORTRESS_AVAILABLE = True
except ImportError:
    FORTRESS_AVAILABLE = False

    # Create dummy decorators
    def database_breaker(func):
        return func

    def shopify_breaker(func):
        return func

    def init_cleanup_middleware(app):
        pass

    class service_status:
        @staticmethod
        def mark_service_down(service, error):
            pass


try:
    from logging_config import setup_logging
except ImportError:

    def setup_logging(app):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)


try:
    from models import db, init_db
except ImportError:
    from flask_sqlalchemy import SQLAlchemy

    db = SQLAlchemy()

    def init_db(app):
        pass


# Fix the schema validation imports:
try:
    from schemas.validation import APIResponseSchema, validate_response

    SCHEMA_VALIDATION_AVAILABLE = True
except ImportError:
    SCHEMA_VALIDATION_AVAILABLE = False

    def validate_response(data):
        return type("MockResponse", (), {"dict": lambda: data})()


def create_app(config_name: Optional[str] = None) -> Flask:
    """
    Fortress Application Factory - Fail fast, recover automatically
    """
    try:
        # STEP 1: Validate configuration (fail fast if invalid)
        if config_name:
            os.environ["ENVIRONMENT"] = config_name

        config = get_config()  # This will raise ConfigValidationError if invalid

    except ConfigValidationError as e:
        # Log to stderr and exit immediately
        print(f"FATAL: Configuration validation failed:\n{e}", file=sys.stderr)
        sys.exit(1)

    # STEP 2: Create Flask app with validated config
    app = Flask(__name__)
    app.config.update(config)

    # STEP 3: Setup logging with error capture
    logger = setup_logging(app)
    logger.info(f"🏰 Creating Fortress App - Environment: {config['ENVIRONMENT']}")

    # STEP 4: Initialize fortress components
    try:
        init_fortress_extensions(app, logger)
        register_fortress_blueprints(app, logger)
        setup_fortress_error_handlers(app, logger)
        init_cleanup_middleware(app)

    except Exception as e:
        logger.error(f"Fortress initialization failed: {e}")
        sys.exit(1)

    # STEP 5: Database initialization with circuit breaker
    with app.app_context():
        try:
            init_fortress_database(app, logger)
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            if config["ENVIRONMENT"] == "production":
                # In production, mark database as down but continue
                service_status.mark_service_down("database", str(e))
                logger.warning("Continuing with database marked as down")
            else:
                sys.exit(1)

    logger.info("🏰 Fortress Application created successfully")
    return app


def init_fortress_extensions(app: Flask, logger: logging.Logger):
    """Initialize extensions with circuit breakers"""

    # Database with circuit breaker
    @database_breaker
    def init_database():
        db.init_app(app)
        return True

    try:
        init_database()
        logger.info("✅ Database extension initialized with circuit breaker")
    except Exception as e:
        logger.error(f"Database extension failed: {e}")
        service_status.mark_service_down("database", str(e))

    # Flask-Login
    from flask_login import LoginManager

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        try:
            from models import User

            return User.query.get(int(user_id))
        except Exception:
            return None

    # Flask-Bcrypt
    from flask_bcrypt import Bcrypt

    Bcrypt(app)

    logger.info("✅ Core extensions initialized")


def register_fortress_blueprints(app: Flask, logger: logging.Logger):
    """Register blueprints with error handling"""
    blueprint_configs = [
        ("core_routes", "core_bp", None),
        ("auth", "auth_bp", None),
        ("shopify_oauth", "oauth_bp", None),
        ("shopify_routes", "shopify_bp", None),
        ("billing", "billing_bp", None),
        ("features_routes", "features_bp", None),
        ("legal_routes", "legal_bp", "/legal"),
    ]

    for module_name, blueprint_name, url_prefix in blueprint_configs:
        try:
            module = __import__(module_name)
            blueprint = getattr(module, blueprint_name)

            if url_prefix:
                app.register_blueprint(blueprint, url_prefix=url_prefix)
            else:
                app.register_blueprint(blueprint)

            logger.info(f"✅ Blueprint {blueprint_name} registered")

        except ImportError as e:
            logger.error(f"❌ Failed to import {module_name}: {e}")
            if module_name in ["core_routes", "auth"]:  # Critical blueprints
                raise
        except Exception as e:
            logger.error(f"❌ Failed to register {blueprint_name}: {e}")
            raise


def setup_fortress_error_handlers(app: Flask, logger: logging.Logger):
    """Setup error handlers with schema validation"""

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Unhandled exception: {e}", exc_info=True)

        # Create validated error response
        error_response = {
            "success": False,
            "error": "An unexpected error occurred",
            "action": "retry",
        }

        # Validate response schema if available
        if SCHEMA_VALIDATION_AVAILABLE:
            validated_response = validate_response(error_response)
            return jsonify(validated_response.dict()), 500
        else:
            return jsonify(error_response), 500

    @app.errorhandler(404)
    def handle_404(e):
        error_response = {
            "success": False,
            "error": "Resource not found",
            "action": "navigate",
        }
        if SCHEMA_VALIDATION_AVAILABLE:
            validated_response = validate_response(error_response)
            return jsonify(validated_response.dict()), 404
        else:
            return jsonify(error_response), 404

    logger.info("✅ Fortress error handlers registered")


@database_breaker
def init_fortress_database(app: Flask, logger: logging.Logger):
    """Initialize database with circuit breaker protection"""

    # Skip heavy operations in production startup
    if (
        app.config.get("ENVIRONMENT") == "production"
        and os.getenv("SKIP_STARTUP_MIGRATIONS") == "true"
    ):
        # Just test connection
        db.session.execute(db.text("SELECT 1"))
        logger.info("✅ Database connection verified (production mode)")
    else:
        init_db(app)
        logger.info("✅ Database initialized with full schema")


def create_fortress_app() -> Flask:
    """Create production fortress app"""
    return create_app("production")


if __name__ == "__main__":
    # Development server with fortress architecture
    try:
        app = create_app("development")
        app.run(host="0.0.0.0", port=5000, debug=False)  # Debug=False for fortress mode
    except ConfigValidationError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)


def init_extensions(app: Flask) -> None:
    """Initialize Flask extensions"""
    logger = logging.getLogger("missioncontrol.factory")

    try:
        # Initialize database
        db.init_app(app)
        logger.info("Database extension initialized")

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

        # Initialize Flask-Bcrypt
        from flask_bcrypt import Bcrypt

        bcrypt = Bcrypt(app)
        logger.info("Flask-Bcrypt initialized")

        # Initialize rate limiter - FIXED: Optional import
        try:
            from rate_limiter import init_limiter

            init_limiter(app)
            logger.info("Rate limiter initialized")
        except ImportError:
            logger.info("Rate limiter disabled - flask_limiter not available")

    except Exception as e:
        logger.error(f"Extension initialization failed: {e}")
        raise
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

        # Register features blueprint (required)
        from features_routes import features_bp

        app.register_blueprint(features_bp)
        logger.info("Features blueprint registered")

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
