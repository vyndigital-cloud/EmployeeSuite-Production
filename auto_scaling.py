"""
Performance Configuration System
Manages performance settings and resource limits.
"""

import logging

logger = logging.getLogger(__name__)

class AutoScaler:
    """Configuration for performance settings."""
    
    def __init__(self):
        self.current_tier = "standard"
        self.max_concurrent_requests = 50
        self.cache_ttl = 300
        self.request_timeout = 30
    
    def get_performance_config(self):
        """Get current performance configuration."""
        return {
            "tier": self.current_tier,
            "max_requests": self.max_concurrent_requests,
            "cache_ttl": self.cache_ttl,
            "timeout": self.request_timeout
        }
    
    def update_config(self, **kwargs):
        """Update performance configuration."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.info(f"Updated performance config: {key} = {value}")

_auto_scaler = None

def get_auto_scaler() -> AutoScaler:
    """Get performance configuration instance."""
    global _auto_scaler
    if _auto_scaler is None:
        _auto_scaler = AutoScaler()
    return _auto_scaler

def init_auto_scaling(app):
    """Initialize performance configuration."""
    get_auto_scaler()
    logger.info("Performance configuration initialized")
