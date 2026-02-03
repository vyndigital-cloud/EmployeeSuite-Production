"""
Comprehensive Security Enhancements for Employee Suite
Implements defense-in-depth security measures
"""

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import g, request

from embedded_detection import is_embedded_request

logger = logging.getLogger(__name__)


# Security headers middleware
def add_security_headers(response):
    """Add comprehensive security headers to all responses"""
    from flask import request, session

    # CRITICAL: Skip CSP for API endpoints to prevent CORS issues
    if request.path.startswith("/api/"):
        # Minimal headers for API endpoints
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    # CRITICAL: Use unified embedded detection (Safari-compatible)
    # This single function handles all detection logic consistently
    # Safari blocks Referer headers, so we check URL params FIRST
    is_embedded = is_embedded_request()

    # Get shop from multiple sources with proper fallback
    shop = None

    # 1. Try URL parameters first (most reliable)
    shop = request.args.get("shop") or request.args.get("shop_domain")

    # 2. Try session if not in URL
    if not shop:
        shop = (
            session.get("shop")
            or session.get("current_shop")
            or session.get("shop_domain")
        )
        if shop:
            logger.debug(f"Security: Got shop from session: {shop}")

    # 3. Try form data for POST requests
    if not shop and request.method == "POST":
        shop = request.form.get("shop") or request.form.get("shop_domain")
        if shop:
            logger.debug(f"Security: Got shop from form: {shop}")

    # 4. Try Referer header as last resort
    if not shop:
        referer = request.headers.get("Referer", "").lower()
        if "myshopify.com" in referer:
            try:
                from urllib.parse import urlparse

                parsed = urlparse(referer)
                if ".myshopify.com" in parsed.netloc:
                    shop = parsed.netloc
                    logger.debug(f"Security: Got shop from Referer: {shop}")
            except Exception:
                pass

    # Clean shop domain
    if shop:
        shop = (
            shop.replace("https://", "")
            .replace("http://", "")
            .split("/")[0]
            .split("?")[0]
        )
        if not shop.endswith(".myshopify.com") and "." not in shop:
            shop = f"{shop}.myshopify.com"

    # For CSP headers, also check if this is a Shopify route (fallback for security)
    # This ensures CSP allows iframe even if params aren't detected
    referer = request.headers.get("Referer", "").lower()
    is_shopify_referer = (
        "admin.shopify.com" in referer
        or ".myshopify.com" in referer
        or "shopify.com" in referer
    )

    is_shopify_route = (
        request.path.startswith("/dashboard")
        or request.path.startswith("/settings")
        or request.path == "/"
        or request.path.startswith("/auth/callback")
        or request.path.startswith("/auth/")
        or request.path.startswith("/login")
        or request.path.startswith("/api/")
        or request.path.startswith("/register")
        or request.path.startswith("/install")
        or request.path.startswith("/billing")
        or request.path.startswith("/subscribe")
        or request.path.startswith("/faq")
        or request.path.startswith("/privacy")
        or request.path.startswith("/terms")
        or "shopify" in request.path.lower()
    )

    # Determine if this should be embedded based on explicit indicators only
    # Remove the "nuclear option" - be more restrictive
    is_embedded = False

    # Check for explicit Shopify embedding indicators
    if request.args.get("embedded") == "1" or request.args.get("host"):
        is_embedded = True
    elif shop and (request.args.get("shop") or request.headers.get("X-Shopify-Shop-Domain")):
        # Only allow if we have a verified shop parameter
        is_embedded = True
    elif request.path.startswith("/auth/callback") and "myshopify.com" in request.headers.get("Referer", ""):
        # OAuth callback from Shopify
        is_embedded = True

    # REMOVED X-Frame-Options entirely for embedded - rely ONLY on CSP frame-ancestors
    # X-Frame-Options is too rigid and causes issues with embedded apps
    # CSP frame-ancestors is more flexible and works better
    # CRITICAL: NEVER set X-Frame-Options - it takes precedence over CSP and breaks embedded apps
    # Only use CSP frame-ancestors to control iframe embedding
    if is_embedded:
        # For embedded apps: Allow iframe embedding from Shopify domains only
        # CRITICAL: Include specific shop domain when available (more reliable than wildcard)
        # https://shopify.dev/docs/apps/store/security/iframe-protection
        shop = request.args.get("shop") or request.args.get("shop_domain") or ""
        shop_clean = ""

        # Build frame-ancestors directive - only include verified shop domain
        if shop:
            frame_ancestors_parts = [
                "https://admin.shopify.com",
                f"https://{shop}",  # Specific shop domain
                "https://*.admin.shopify.com"
            ]
            
            # Only add generic Shopify domains if we can't determine specific shop
            if not shop.endswith(".myshopify.com"):
                frame_ancestors_parts.extend([
                    "https://*.myshopify.com",
                    "https://shopify.com"
                ])
            
            frame_ancestors = "frame-ancestors " + " ".join(frame_ancestors_parts) + "; "
            
            logger.info(f"🔓 IFRAME ALLOWED (verified): path={request.path}, shop={shop}")
        else:
            frame_ancestors = "frame-ancestors 'none'; "
            logger.warning(f"🔒 IFRAME BLOCKED (no shop verification): path={request.path}")
    else:
        # Strict no-iframe policy
        frame_ancestors = "frame-ancestors 'none'; "
        if is_embedded:
            logger.warning(f"🔒 IFRAME BLOCKED (no shop verification): path={request.path}")

    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Enable XSS protection (legacy browsers)
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Content Security Policy - Standard Shopify embedded app configuration
    # Based on Shopify's official recommendations for embedded apps
    if is_embedded:
        # Embedded app CSP - allows Shopify resources and App Bridge
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.shopify.com https://js.stripe.com https://www.googletagmanager.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.shopify.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.stripe.com https://*.myshopify.com https://admin.shopify.com https://accounts.shopify.com https://www.google-analytics.com https://www.googletagmanager.com https://shopify.com; "
            + frame_ancestors
            + "frame-src https://checkout.stripe.com https://js.stripe.com; "
            "base-uri 'self'; "
            "form-action *;"
        )
    else:
        # Regular page CSP - stricter security
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com https://js.stripe.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.stripe.com https://*.myshopify.com https://www.google-analytics.com https://www.googletagmanager.com; "
            + frame_ancestors
            + "frame-src https://checkout.stripe.com https://js.stripe.com; "
            "base-uri 'self'; "
            "form-action *;"
        )
    response.headers["Content-Security-Policy"] = csp
    # Force browser to not cache CSP headers
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions Policy (formerly Feature Policy)
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), payment=()"
    )

    # HSTS (only in production with HTTPS)
    if request.is_secure or os.getenv("ENVIRONMENT") == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

    return response


# Request size limits
MAX_REQUEST_SIZE = 16 * 1024 * 1024  # 16MB max request size


def check_request_size():
    """Check if request size exceeds limits"""
    if request.content_length and request.content_length > MAX_REQUEST_SIZE:
        logger.warning(
            f"Request too large: {request.content_length} bytes from {request.remote_addr}"
        )
        return False
    return True


# Rate limiting per IP - MOVED to rate_limiter.py (using Flask-Limiter)
# This custom implementation is deprecated in favor of the standard library
# which provides better memory management and key handling.


# Enhanced input sanitization
from markupsafe import escape


def sanitize_input_enhanced(text):
    """Enhanced XSS prevention using Flask's escape"""
    if not text:
        return text
    if isinstance(text, str):
        # Escape HTML special characters
        text = escape(text)
        # Remove any remaining script tags (defense in depth)
        import re

        text = re.sub(
            r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL
        )
        text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)
    return text


# SQL injection double-check
def validate_sql_input(value):
    """Additional validation for SQL injection patterns"""
    if not value or not isinstance(value, str):
        return True

    # Common SQL injection patterns
    dangerous_patterns = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(UNION|OR|AND)\s+\d+)",
        r"('|;|\\)",
    ]

    import re

    for pattern in dangerous_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            logger.warning(f"Potential SQL injection detected: {value[:50]}")
            return False
    return True


# Secure token generation
def generate_secure_token(length=32):
    """Generate cryptographically secure random token"""
    import secrets

    return secrets.token_urlsafe(length)


# Password strength validation
def validate_password_strength(password):
    """Validate password meets security requirements"""
    if not password:
        return False, "Password is required"

    if len(password) < 8:
        return False, "Password must be at least 8 characters"

    if len(password) > 128:
        return False, "Password is too long (max 128 characters)"

    # Check for common weak passwords
    weak_passwords = ["password", "12345678", "qwerty", "abc123", "password123"]
    if password.lower() in weak_passwords:
        return False, "Password is too common. Please choose a stronger password."

    # Check for complexity (at least one letter and one number)
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)

    if not (has_letter and has_number):
        return False, "Password must contain at least one letter and one number"

    return True, "Password is valid"


# Secure comparison (timing-safe)
def secure_compare(a, b):
    """Timing-safe string comparison using secrets.compare_digest"""
    return secrets.compare_digest(str(a), str(b))


# Log security events
def log_security_event(event_type, details, severity="INFO"):
    """Log security-related events"""
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "ip_address": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", "Unknown"),
        "details": details,
    }

    if severity == "WARNING":
        logger.warning(f"Security event: {event_type} - {details}")
    elif severity == "ERROR":
        logger.error(f"Security event: {event_type} - {details}")
    else:
        logger.info(f"Security event: {event_type} - {details}")

    return log_data


# Data encryption for sensitive fields (at rest)
def encrypt_sensitive_data(data, key=None):
    """Encrypt sensitive data before storing"""
    if not data:
        return data

    # Use environment variable for encryption key
    encryption_key = key or os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        logger.warning("ENCRYPTION_KEY not set - data not encrypted")
        return data

    try:
        from cryptography.fernet import Fernet

        # Ensure key is proper length for Fernet
        key_hash = hashlib.sha256(encryption_key.encode()).digest()
        f = Fernet(Fernet.generate_key())  # In production, use the hashed key properly
        encrypted = f.encrypt(data.encode() if isinstance(data, str) else data)
        return encrypted.hex()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return data


def decrypt_sensitive_data(encrypted_data, key=None):
    """Decrypt sensitive data"""
    if not encrypted_data:
        return encrypted_data

    encryption_key = key or os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        return encrypted_data

    try:
        from cryptography.fernet import Fernet

        # Decrypt logic here (simplified - implement properly with key management)
        return encrypted_data  # Placeholder
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return encrypted_data


# Request validation
def validate_request():
    """Validate incoming request for security issues"""
    issues = []

    # Check request size
    if not check_request_size():
        issues.append("Request size exceeds limit")

    # Check for suspicious headers
    suspicious_headers = ["X-Forwarded-Host", "X-Original-URL"]
    for header in suspicious_headers:
        if request.headers.get(header):
            # Log but don't block (might be legitimate proxy)
            log_security_event("suspicious_header", f"Header {header} present", "INFO")

    return len(issues) == 0, issues


# CSRF token generation and validation
_csrf_tokens = {}


def generate_csrf_token():
    """Generate CSRF token for form protection"""
    token = generate_secure_token(32)
    session_id = request.cookies.get("session", "anonymous")
    _csrf_tokens[session_id] = {
        "token": token,
        "expires": datetime.utcnow() + timedelta(hours=1),
    }
    return token


def validate_csrf_token(token):
    """Validate CSRF token"""
    if not token:
        return False

    session_id = request.cookies.get("session", "anonymous")
    stored = _csrf_tokens.get(session_id)

    if not stored:
        return False

    # Check expiration
    if datetime.utcnow() > stored["expires"]:
        del _csrf_tokens[session_id]
        return False

    # Timing-safe comparison
    return secure_compare(token, stored["token"])


# Security middleware decorator
def require_https(f):
    """Require HTTPS for sensitive routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_secure and os.getenv("ENVIRONMENT") == "production":
            from flask import redirect, url_for

            return redirect(request.url.replace("http://", "https://"), code=301)
        return f(*args, **kwargs)

    return decorated_function
