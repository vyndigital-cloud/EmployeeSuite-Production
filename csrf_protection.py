"""
Simple CSRF Protection System for MissionControl
Provides basic Cross-Site Request Forgery protection without Flask-WTF dependency
"""

import hashlib
import hmac
import logging
import secrets
import time
from functools import wraps
from typing import Any, Dict, Optional

from flask import abort, g, jsonify, request, session

from config import config

logger = logging.getLogger("missioncontrol.csrf")


class SimpleCSRFManager:
    """Simple CSRF protection manager without Flask-WTF dependency"""

    def __init__(self, app=None):
        self.app = app
        # Token storage (in production, use Redis or database)
        self._tokens: Dict[str, Dict[str, Any]] = {}

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize CSRF protection with Flask app"""
        self.app = app

        # Configure basic CSRF settings
        app.config["CSRF_ENABLED"] = getattr(config, "WTF_CSRF_ENABLED", True)
        app.config["CSRF_TIME_LIMIT"] = getattr(config, "WTF_CSRF_TIME_LIMIT", 3600)
        app.config["CSRF_SECRET_KEY"] = getattr(config, "SECRET_KEY", "dev-secret")

        # Before request handler to set up CSRF context
        @app.before_request
        def csrf_before_request():
            self._setup_csrf_context()

        logger.info("Simple CSRF protection initialized")

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
        # Skip for webhooks
        if request.path.startswith("/webhooks/") or request.path.startswith(
            "/webhook/"
        ):
            return True

        # Skip for API endpoints with proper authentication
        if request.path.startswith("/api/") and self._has_valid_api_auth():
            return True

        # Skip for Shopify OAuth callbacks
        if request.path.startswith("/auth/callback"):
            return True

        # Skip for health checks
        if request.path in ["/health", "/favicon.ico", "/robots.txt"]:
            return True

        return False

    def _has_valid_api_auth(self) -> bool:
        """Check if request has valid API authentication"""
        # Check for JWT token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return True

        # Check for Shopify session token
        if request.headers.get("X-Shopify-Shop-Domain"):
            return True

        return False

    def generate_token(self, session_id: Optional[str] = None) -> str:
        """Generate a new CSRF token"""
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

        return full_token

    def _sign_token(self, token_payload: str) -> str:
        """Sign token payload with secret key"""
        secret_key = self.app.config.get("CSRF_SECRET_KEY", "dev-secret")
        key = secret_key.encode("utf-8")
        message = token_payload.encode("utf-8")
        signature = hmac.new(key, message, hashlib.sha256).hexdigest()
        return signature[:16]  # Truncate for brevity

    def validate_token(self, token: str, session_id: Optional[str] = None) -> bool:
        """Validate a CSRF token"""
        if not token:
            return False

        try:
            # Parse token
            parts = token.split(":")
            if len(parts) != 3:
                return False

            token_data, timestamp_str, signature = parts

            # Verify signature
            token_payload = f"{token_data}:{timestamp_str}"
            expected_signature = self._sign_token(token_payload)

            if not hmac.compare_digest(signature, expected_signature):
                return False

            # Check if token exists
            if token_data not in self._tokens:
                return False

            token_info = self._tokens[token_data]

            # Check session matching
            if session_id is None:
                session_id = session.get("_id", "anonymous")

            if token_info["session_id"] != session_id:
                return False

            # Check expiration
            time_limit = self.app.config.get("CSRF_TIME_LIMIT", 3600)
            token_age = int(time.time()) - token_info["created_at"]
            if token_age > time_limit:
                return False

            return True

        except Exception as e:
            logger.error(f"CSRF token validation error: {e}")
            return False

    def _cleanup_old_tokens(self):
        """Remove expired tokens from storage"""
        current_time = int(time.time())
        time_limit = self.app.config.get("CSRF_TIME_LIMIT", 3600)
        expired_tokens = []

        for token_data, token_info in self._tokens.items():
            token_age = current_time - token_info["created_at"]
            if token_age > time_limit + 3600:  # Grace period
                expired_tokens.append(token_data)

        for token_data in expired_tokens:
            del self._tokens[token_data]


# Global CSRF manager instance
csrf_manager = SimpleCSRFManager()


def init_csrf_protection(app):
    """Initialize CSRF protection for the application"""
    csrf_manager.init_app(app)
    return csrf_manager


def require_csrf(f):
    """Decorator to require CSRF token validation for a view"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip if already marked as exempt
        if getattr(g, "csrf_exempt", False):
            return f(*args, **kwargs)

        # Skip if CSRF is disabled
        if not csrf_manager.app.config.get("CSRF_ENABLED", True):
            return f(*args, **kwargs)

        # Get token from various sources
        token = (
            request.form.get("csrf_token")
            or request.headers.get("X-CSRFToken")
            or request.headers.get("X-CSRF-Token")
        )

        if not token:
            if request.is_json:
                return jsonify({"error": "Missing CSRF token"}), 400
            else:
                abort(400, description="Missing CSRF token")

        # Validate token
        if not csrf_manager.validate_token(token):
            if request.is_json:
                return jsonify({"error": "Invalid CSRF token"}), 400
            else:
                abort(400, description="Invalid CSRF token")

        return f(*args, **kwargs)

    return decorated_function


def csrf_exempt(f):
    """Decorator to exempt a view from CSRF protection"""

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


logger.info("Simple CSRF protection module loaded")
