from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

def init_limiter(app):
    """Initialize rate limiter with smart defaults"""
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["100 per hour"],  # Global limit for all routes
        storage_uri="memory://",
        headers_enabled=True
    )
    
    return limiter
