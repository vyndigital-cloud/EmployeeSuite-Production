"""
Enterprise Security Implementation
Implements advanced security measures for 100k+ users
"""

import hashlib
import hmac
import logging
import os
import time
from functools import wraps

import jwt
from flask import g, jsonify, request

logger = logging.getLogger(__name__)


class EnterpriseSecurityManager:
    def __init__(self):
        self.api_secret = os.getenv("SHOPIFY_API_SECRET")
        self.rate_limits = {}
        self.failed_attempts = {}

    def validate_request_signature(self, data, signature):
        """Validate request signature for API security"""
        if not signature or not self.api_secret:
            return False

        expected = hmac.new(
            self.api_secret.encode(),
            data.encode() if isinstance(data, str) else data,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def check_rate_limit(self, identifier, limit=1000, window=3600):
        """Advanced rate limiting per user/shop"""
        now = time.time()
        window_start = now - window

        # Clean old entries
        if identifier in self.rate_limits:
            self.rate_limits[identifier] = [
                timestamp
                for timestamp in self.rate_limits[identifier]
                if timestamp > window_start
            ]
        else:
            self.rate_limits[identifier] = []

        # Check limit
        if len(self.rate_limits[identifier]) >= limit:
            return False

        # Add current request
        self.rate_limits[identifier].append(now)
        return True

    def log_security_event(self, event_type, details, severity="INFO"):
        """Enhanced security event logging"""
        security_log = {
            "timestamp": time.time(),
            "event_type": event_type,
            "severity": severity,
            "details": details,
            "request_ip": request.remote_addr if request else None,
            "user_agent": request.headers.get("User-Agent") if request else None,
        }

        logger.info(f"SECURITY_EVENT: {security_log}")

        # In production, send to SIEM system
        # self.send_to_siem(security_log)


security_manager = EnterpriseSecurityManager()


def require_signature(f):
    """Decorator to require request signature validation"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        signature = request.headers.get("X-Signature")
        data = request.get_data()

        if not security_manager.validate_request_signature(data, signature):
            security_manager.log_security_event(
                "INVALID_SIGNATURE",
                {"endpoint": request.endpoint, "ip": request.remote_addr},
                "WARNING",
            )
            return jsonify({"error": "Invalid signature"}), 401

        return f(*args, **kwargs)

    return decorated_function


def enterprise_rate_limit(limit=1000, window=3600):
    """Enterprise rate limiting decorator"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get identifier (user ID, shop, or IP)
            identifier = request.remote_addr

            if hasattr(g, "current_user") and g.current_user:
                identifier = f"user:{g.current_user.id}"
            elif request.args.get("shop"):
                identifier = f"shop:{request.args.get('shop')}"

            if not security_manager.check_rate_limit(identifier, limit, window):
                security_manager.log_security_event(
                    "RATE_LIMIT_EXCEEDED",
                    {"identifier": identifier, "endpoint": request.endpoint},
                    "WARNING",
                )
                return jsonify({"error": "Rate limit exceeded"}), 429

            return f(*args, **kwargs)

        return decorated_function

    return decorator
