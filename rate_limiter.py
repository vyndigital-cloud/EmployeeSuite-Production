from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

def init_limiter(app):
    """Initialize rate limiter with route-specific limits"""
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour"],
        storage_uri="memory://",
        headers_enabled=True
    )
    return limiter

def apply_rate_limits(limiter, auth_bp, billing_bp):
    """Apply specific rate limits to routes after blueprints are registered"""
    limiter.limit("10 per minute")(auth_bp.view_functions['login'])
    limiter.limit("5 per hour")(auth_bp.view_functions['register'])
    limiter.limit("20 per hour")(billing_bp.view_functions['create_checkout'])
