from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

def init_limiter(app):
    """Initialize rate limiter with global limit"""
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour"],
        storage_uri="memory://",
        headers_enabled=True
    )
    return limiter
