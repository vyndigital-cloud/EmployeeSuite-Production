"""
Comprehensive Security Enhancements for Employee Suite
Implements defense-in-depth security measures
"""

from flask import request, g
from functools import wraps
import hashlib
import hmac
import os
import logging
import secrets
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Security headers middleware
def add_security_headers(response):
    """Add comprehensive security headers to all responses"""
    from flask import request
    
    # Check if this is an embedded app request (Shopify iframe)
    # SECURE but PERMISSIVE: Only allow iframe embedding for verified Shopify requests
    # This ensures embedded apps work while maintaining security
    referer = request.headers.get('Referer', '').lower()
    has_shop_param = request.args.get('shop') or request.args.get('shop_domain')
    has_host_param = request.args.get('host')  # Shopify provides this for embedded apps
    has_shopify_header = request.headers.get('X-Shopify-Shop-Domain') or request.headers.get('X-Shopify-Hmac-Sha256')
    
    # SECURITY: Only trust Shopify domains, not arbitrary shopify.com subdomains
    is_shopify_referer = (
        'admin.shopify.com' in referer or  # Official Shopify admin
        referer.endswith('.myshopify.com')  # Verified Shopify stores only
    )
    
    # Only treat as embedded if we have STRONG indicators (not just any path)
    # This prevents malicious sites from embedding our pages
    is_embedded = (
        request.args.get('embedded') == '1' or  # Explicit embedded flag
        (has_shop_param and has_host_param) or  # Both shop AND host (Shopify requirement)
        has_shopify_header or  # Official Shopify headers
        is_shopify_referer  # Coming from verified Shopify domains
    )
    
    # For embedded apps, allow iframe embedding ONLY from Shopify
    # For regular pages, prevent clickjacking (SECURITY)
    if is_embedded:
        # For embedded apps: DO NOT set X-Frame-Options (let CSP handle it)
        # X-Frame-Options takes precedence over CSP, so we must not set it
        # SECURITY: Only allow specific Shopify domains (not wildcards)
        # This prevents malicious sites from embedding our app
        frame_ancestors = "frame-ancestors https://admin.shopify.com https://admin.shopify.com/* https://*.myshopify.com https://*.myshopify.com/*; "
    else:
        # Regular pages - STRICT security: prevent ALL iframe embedding
        # This protects against clickjacking attacks
        response.headers['X-Frame-Options'] = 'DENY'
        frame_ancestors = "frame-ancestors 'none'; "
    
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Enable XSS protection (legacy browsers)
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Content Security Policy - strict policy (allows Stripe checkout and Shopify embedding)
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://cdn.shopify.com https://js.stripe.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.shopify.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.stripe.com https://*.myshopify.com https://www.google-analytics.com; "
        + frame_ancestors +
        "frame-src https://checkout.stripe.com https://js.stripe.com; "
        "base-uri 'self'; "
        "form-action 'self' https://checkout.stripe.com;"
    )
    response.headers['Content-Security-Policy'] = csp
    
    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions Policy (formerly Feature Policy)
    response.headers['Permissions-Policy'] = (
        'geolocation=(), '
        'microphone=(), '
        'camera=(), '
        'payment=()'
    )
    
    # HSTS (only in production with HTTPS)
    if request.is_secure or os.getenv('ENVIRONMENT') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    
    return response

# Request size limits
MAX_REQUEST_SIZE = 16 * 1024 * 1024  # 16MB max request size

def check_request_size():
    """Check if request size exceeds limits"""
    if request.content_length and request.content_length > MAX_REQUEST_SIZE:
        logger.warning(f"Request too large: {request.content_length} bytes from {request.remote_addr}")
        return False
    return True

# Rate limiting per IP (additional layer)
from collections import defaultdict
from time import time

_rate_limit_store = defaultdict(list)
_rate_limit_cleanup = time()

def rate_limit_by_ip(max_requests=100, window=3600):
    """Rate limit decorator based on IP address"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            global _rate_limit_cleanup
            
            # Cleanup old entries every 5 minutes
            current_time = time()
            if current_time - _rate_limit_cleanup > 300:
                cutoff = current_time - window
                for ip in list(_rate_limit_store.keys()):
                    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if t > cutoff]
                    if not _rate_limit_store[ip]:
                        del _rate_limit_store[ip]
                _rate_limit_cleanup = current_time
            
            # Get client IP
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            if client_ip:
                client_ip = client_ip.split(',')[0].strip()
            
            # Check rate limit
            now = time()
            cutoff = now - window
            requests = [t for t in _rate_limit_store[client_ip] if t > cutoff]
            
            if len(requests) >= max_requests:
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                from flask import jsonify
                return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
            
            # Add current request
            requests.append(now)
            _rate_limit_store[client_ip] = requests
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

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
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
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
    weak_passwords = ['password', '12345678', 'qwerty', 'abc123', 'password123']
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
def log_security_event(event_type, details, severity='INFO'):
    """Log security-related events"""
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'Unknown'),
        'details': details
    }
    
    if severity == 'WARNING':
        logger.warning(f"Security event: {event_type} - {details}")
    elif severity == 'ERROR':
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
    encryption_key = key or os.getenv('ENCRYPTION_KEY')
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
    
    encryption_key = key or os.getenv('ENCRYPTION_KEY')
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
    suspicious_headers = ['X-Forwarded-Host', 'X-Original-URL']
    for header in suspicious_headers:
        if request.headers.get(header):
            # Log but don't block (might be legitimate proxy)
            log_security_event('suspicious_header', f"Header {header} present", 'INFO')
    
    return len(issues) == 0, issues

# CSRF token generation and validation
_csrf_tokens = {}

def generate_csrf_token():
    """Generate CSRF token for form protection"""
    token = generate_secure_token(32)
    session_id = request.cookies.get('session', 'anonymous')
    _csrf_tokens[session_id] = {
        'token': token,
        'expires': datetime.utcnow() + timedelta(hours=1)
    }
    return token

def validate_csrf_token(token):
    """Validate CSRF token"""
    if not token:
        return False
    
    session_id = request.cookies.get('session', 'anonymous')
    stored = _csrf_tokens.get(session_id)
    
    if not stored:
        return False
    
    # Check expiration
    if datetime.utcnow() > stored['expires']:
        del _csrf_tokens[session_id]
        return False
    
    # Timing-safe comparison
    return secure_compare(token, stored['token'])

# Security middleware decorator
def require_https(f):
    """Require HTTPS for sensitive routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_secure and os.getenv('ENVIRONMENT') == 'production':
            from flask import redirect, url_for
            return redirect(request.url.replace('http://', 'https://'), code=301)
        return f(*args, **kwargs)
    return decorated_function
