"""
CSRF Protection System for MissionControl
Provides comprehensive Cross-Site Request Forgery protection using Flask-WTF
"""

import hashlib
import hmac
import logging
import secrets
import time
from functools import wraps
from typing import Any, Dict, Optional, Tuple

from flask import abort, current_app, g, jsonify, request, session
from flask_wtf.csrf import CSRFProtect, validate_csrf
from werkzeug.exceptions import BadRequest

from config import config

logger = logging.getLogger("missioncontrol.csrf")


class CSRFManager:
    """Enhanced CSRF protection manager"""

    def __init__(self, app=None):
        self.app = app
        self.csrf = CSRFProtect()

        # Token storage (in production, use Redis or database)
        self._tokens: Dict[str, Dict[str, Any]] = {}

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize CSRF protection with Flask app"""
        self.app = app
        self.csrf.init_app(app)

        # Configure CSRF settings
        app.config["WTF_CSRF_ENABLED"] = config.WTF_CSRF_ENABLED
        app.config["WTF_CSRF_TIME_LIMIT"] = config.WTF_CSRF_TIME_LIMIT
        app.config["WTF_CSRF_SECRET_KEY"] = config.SECRET_KEY

        # Custom error handler for CSRF failures (Flask-WTF 1.2+ API)
        from flask_wtf.csrf import CSRFError

        @app.errorhandler(CSRFError)
        def csrf_error(e):
            logger.warning(f"CSRF validation failed: {e.description}")

            if request.is_json:
                return jsonify(
                    {
                        "error": "CSRF token validation failed",
                        "message": "Request blocked for security reasons",
                        "code": "CSRF_ERROR",
                    }
                ), 400
            else:
                return abort(400, description="CSRF token validation failed")

        # Before request handler to set up CSRF context
        @app.before_request
        def csrf_before_request():
            self._setup_csrf_context()

        logger.info("CSRF protection initialized")

    def _setup_csrf_context(self):
        """Setup CSRF context for current request"""
        # Skip CSRF for certain routes
        if self._should_skip_csrf():
            g.csrf_exempt = True
            return

        # Generate token for session if needed
        if "csrf_token" not in session:
            session["csrf_token"] = self.generate_token()

        # Store token in g for template access
        g.csrf_token = session.get("csrf_token")

    def _should_skip_csrf(self) -> bool:
        """Determine if CSRF should be skipped for current request"""
        # Skip for webhooks (they use HMAC verification)
        webhook_endpoints = [
            "webhook_shopify.handle_webhook",
            "webhook_stripe.handle_webhook",
            "api.health_check",
        ]

        if request.endpoint in webhook_endpoints:
            return True

        # Skip for API endpoints with proper authentication
        if request.path.startswith("/api/") and self._has_valid_api_auth():
            return True

        # Skip for Shopify OAuth callbacks
        if request.path.startswith("/auth/callback"):
            return True

        return False

    def _has_valid_api_auth(self) -> bool:
        """Check if request has valid API authentication"""
        # Check for JWT token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return True  # JWT validation would happen elsewhere

        # Check for API key authentication
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return True  # API key validation would happen elsewhere

        return False

    def generate_token(self, session_id: Optional[str] = None) -> str:
        """
        Generate a new CSRF token

        Args:
            session_id: Optional session ID for token scoping

        Returns:
            CSRF token string
        """
        # Use session ID from Flask session if not provided
        if session_id is None:
            session_id = session.get("_id", "anonymous")

        # Generate random token
        token_data = secrets.token_urlsafe(32)
        timestamp = int(time.time())

        # Create token with timestamp
        token_payload = f"{token_data}:{timestamp}"

        # Sign the token
        signature = self._sign_token(token_payload)
        full_token = f"{token_payload}:{signature}"

        # Store token metadata
        self._tokens[token_data] = {
            "session_id": session_id,
            "created_at": timestamp,
            "used": False,
        }

        # Clean up old tokens
        self._cleanup_old_tokens()

        logger.debug(f"Generated CSRF token for session: {session_id}")
        return full_token

    def _sign_token(self, token_payload: str) -> str:
        """Sign token payload with secret key"""
        key = config.SECRET_KEY.encode("utf-8")
        message = token_payload.encode("utf-8")
        signature = hmac.new(key, message, hashlib.sha256).hexdigest()
        return signature[:16]  # Truncate for brevity

    def validate_token(self, token: str, session_id: Optional[str] = None) -> bool:
        """
        Validate a CSRF token

        Args:
            token: CSRF token to validate
            session_id: Optional session ID for validation

        Returns:
            True if token is valid
        """
        if not token:
            return False

        try:
            # Parse token
            parts = token.split(":")
            if len(parts) != 3:
                logger.warning("Invalid CSRF token format")
                return False

            token_data, timestamp_str, signature = parts

            # Verify signature
            token_payload = f"{token_data}:{timestamp_str}"
            expected_signature = self._sign_token(token_payload)

            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("CSRF token signature mismatch")
                return False

            # Check if token exists in our storage
            if token_data not in self._tokens:
                logger.warning("CSRF token not found in storage")
                return False

            token_info = self._tokens[token_data]

            # Check session matching
            if session_id is None:
                session_id = session.get("_id", "anonymous")

            if token_info["session_id"] != session_id:
                logger.warning("CSRF token session mismatch")
                return False

            # Check expiration
            token_age = int(time.time()) - token_info["created_at"]
            if token_age > config.WTF_CSRF_TIME_LIMIT:
                logger.warning("CSRF token expired")
                return False

            # Check if token was already used (prevent replay attacks)
            if token_info["used"]:
                logger.warning("CSRF token already used")
                return False

            # Mark token as used
            token_info["used"] = True

            logger.debug("CSRF token validation successful")
            return True

        except Exception as e:
            logger.error(f"CSRF token validation error: {e}")
            return False

    def _cleanup_old_tokens(self):
        """Remove expired tokens from storage"""
        current_time = int(time.time())
        expired_tokens = []

        for token_data, token_info in self._tokens.items():
            token_age = current_time - token_info["created_at"]
            if token_age > config.WTF_CSRF_TIME_LIMIT + 3600:  # Grace period
                expired_tokens.append(token_data)

        for token_data in expired_tokens:
            del self._tokens[token_data]

        if expired_tokens:
            logger.debug(f"Cleaned up {len(expired_tokens)} expired CSRF tokens")


# Global CSRF manager instance
csrf_manager = CSRFManager()


def init_csrf_protection(app):
    """Initialize CSRF protection for the application"""
    csrf_manager.init_app(app)
    return csrf_manager


def require_csrf(f):
    """
    Decorator to require CSRF token validation for a view

    Usage:
        @app.route('/protected')
        @require_csrf
        def protected_view():
            return 'Protected!'
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip if already marked as exempt
        if getattr(g, "csrf_exempt", False):
            return f(*args, **kwargs)

        # Skip if CSRF is disabled
        if not config.WTF_CSRF_ENABLED:
            return f(*args, **kwargs)

        # Get token from various sources
        token = (
            request.form.get("csrf_token")
            or request.headers.get("X-CSRFToken")
            or request.headers.get("X-CSRF-Token")
        )

        if not token:
            logger.warning(f"Missing CSRF token for {request.endpoint}")
            if request.is_json:
                return jsonify(
                    {
                        "error": "Missing CSRF token",
                        "message": "CSRF token is required for this request",
                    }
                ), 400
            else:
                abort(400, description="Missing CSRF token")

        # Validate token
        if not csrf_manager.validate_token(token):
            logger.warning(f"Invalid CSRF token for {request.endpoint}")
            if request.is_json:
                return jsonify(
                    {
                        "error": "Invalid CSRF token",
                        "message": "CSRF token validation failed",
                    }
                ), 400
            else:
                abort(400, description="Invalid CSRF token")

        return f(*args, **kwargs)

    return decorated_function


def csrf_exempt(f):
    """
    Decorator to exempt a view from CSRF protection

    Usage:
        @app.route('/webhook')
        @csrf_exempt
        def webhook():
            return 'OK'
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.csrf_exempt = True
        return f(*args, **kwargs)

    return decorated_function


def get_csrf_token() -> str:
    """Get CSRF token for current session"""
    if hasattr(g, "csrf_token") and g.csrf_token:
        return g.csrf_token

    # Generate new token if not exists
    token = csrf_manager.generate_token()
    session["csrf_token"] = token
    g.csrf_token = token

    return token


def validate_csrf_token(token: str) -> bool:
    """Validate a CSRF token"""
    return csrf_manager.validate_token(token)


# Template context processor to make CSRF token available in templates
def csrf_token_processor():
    """Template context processor for CSRF token"""
    return dict(csrf_token=get_csrf_token)


# Flask-WTF integration helpers
def generate_csrf_secret():
    """Generate a CSRF secret for Flask-WTF"""
    return secrets.token_hex(16)


class CSRFForm:
    """Base class for forms with CSRF protection"""

    def __init__(self):
        self.csrf_token = get_csrf_token()

    def validate_csrf(self) -> bool:
        """Validate CSRF token for this form"""
        token = request.form.get("csrf_token")
        return validate_csrf_token(token) if token else False


# Security middleware for automatic CSRF protection
def csrf_protection_middleware(app):
    """Middleware to automatically protect forms and AJAX requests"""

    @app.before_request
    def check_csrf():
        # Skip GET, HEAD, OPTIONS requests
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return

        # Skip if explicitly exempted
        if getattr(g, "csrf_exempt", False):
            return

        # Skip if CSRF disabled
        if not config.WTF_CSRF_ENABLED:
            return

        # Check for CSRF token
        token = (
            request.form.get("csrf_token")
            or request.headers.get("X-CSRFToken")
            or request.headers.get("X-CSRF-Token")
        )

        if not token or not validate_csrf_token(token):
            logger.warning(f"CSRF protection blocked request to {request.endpoint}")

            if request.is_json:
                return jsonify(
                    {
                        "error": "CSRF validation failed",
                        "message": "Request blocked for security reasons",
                    }
                ), 403
            else:
                abort(403, description="CSRF validation failed")


# Utility functions for testing
def disable_csrf_for_testing():
    """Disable CSRF protection for testing"""
    if config.is_testing():
        config.WTF_CSRF_ENABLED = False
        logger.info("CSRF protection disabled for testing")


def enable_csrf_for_testing():
    """Re-enable CSRF protection after testing"""
    if config.is_testing():
        config.WTF_CSRF_ENABLED = True
        logger.info("CSRF protection re-enabled after testing")


logger.info("CSRF protection module loaded")
