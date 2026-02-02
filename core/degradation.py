"""
Simplified graceful degradation
"""

import logging
from functools import wraps

logger = logging.getLogger(__name__)


class ServiceStatus:
    def __init__(self):
        self.services = {}

    def mark_service_down(self, service_name, error):
        self.services[service_name] = {"status": "down", "error": error}
        logger.warning(f"Service {service_name} marked as down: {error}")

    def mark_service_up(self, service_name):
        self.services[service_name] = {"status": "up"}


service_status = ServiceStatus()


def with_graceful_degradation(service_name, fallback_data=None):
    """Graceful degradation decorator"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Service {service_name} failed, using fallback: {e}")
                return fallback_data or {
                    "success": False,
                    "error": f"{service_name} temporarily unavailable",
                }

        return wrapper

    return decorator
