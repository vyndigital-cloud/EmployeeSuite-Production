from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import has_request_context

def get_remote_address_safe():
    """Get remote address safely - handles missing request context"""
    if has_request_context():
        return get_remote_address()
    # Fallback for when called outside request context (during initialization)
    return "127.0.0.1"

def init_limiter(app):
    """Initialize rate limiter with global limit"""
    limiter = Limiter(
        app=app,
        key_func=get_remote_address_safe,
        default_limits=["200 per hour"],
        storage_uri="memory://",
        headers_enabled=True
    )
    return limiter
