"""
Simplified cleanup middleware
"""

import logging

logger = logging.getLogger(__name__)


def init_cleanup_middleware(app):
    """Initialize basic cleanup middleware"""

    @app.after_request
    def cleanup_after_request(response):
        try:
            # Basic cleanup
            from models import db

            if hasattr(db, "session") and db.session.is_active:
                db.session.remove()
        except Exception as e:
            logger.debug(f"Cleanup error: {e}")
        return response

    logger.info("Cleanup middleware initialized")
