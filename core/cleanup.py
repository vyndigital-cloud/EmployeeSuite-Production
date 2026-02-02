"""
Automated Cleanup Middleware - Prevent memory leaks and stale connections
Runs after every request to maintain system health
"""
import gc
import logging
import time
from flask import g, request
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Optional psutil import
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class CleanupManager:
    def __init__(self):
        self.request_count = 0
        self.last_major_cleanup = time.time()
        self.memory_threshold = 85  # Trigger cleanup at 85% memory usage
        
    def before_request(self):
        """Setup request tracking"""
        g.request_start_time = time.time()
        g.request_id = f"{int(time.time())}-{id(request)}"
        
    def after_request(self, response):
        """Cleanup after each request"""
        try:
            self.request_count += 1
            
            # Basic cleanup every request
            self._basic_cleanup()
            
            # Memory-based cleanup
            if self._should_run_memory_cleanup():
                self._memory_cleanup()
            
            # Periodic deep cleanup
            if self._should_run_deep_cleanup():
                self._deep_cleanup()
                
            # Log request performance
            self._log_request_performance()
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        
        return response
    
    def _basic_cleanup(self):
        """Run after every request"""
        # Clear Flask g object
        if hasattr(g, 'temp_data'):
            delattr(g, 'temp_data')
        
        # Database session cleanup
        try:
            from models import db
            if db.session.is_active:
                db.session.remove()
        except Exception as e:
            logger.debug(f"DB cleanup error: {e}")
    
    def _should_run_memory_cleanup(self) -> bool:
        """Check if memory cleanup is needed"""
        if not PSUTIL_AVAILABLE:
            return False
        try:
            memory_percent = psutil.virtual_memory().percent
            return memory_percent > self.memory_threshold
        except:
            return False
    
    def _memory_cleanup(self):
        """Aggressive memory cleanup"""
        logger.info("Running memory cleanup due to high usage")
        
        # Clear performance cache
        try:
            from performance import clear_cache
            clear_cache()
        except:
            pass
        
        # Force garbage collection
        collected = gc.collect()
        logger.info(f"Garbage collection freed {collected} objects")
    
    def _should_run_deep_cleanup(self) -> bool:
        """Check if deep cleanup is needed (every 100 requests or 5 minutes)"""
        return (
            self.request_count % 100 == 0 or
            time.time() - self.last_major_cleanup > 300
        )
    
    def _deep_cleanup(self):
        """Deep cleanup - runs periodically"""
        logger.info("Running deep cleanup")
        self.last_major_cleanup = time.time()
        
        # Clear all caches
        try:
            from performance import clear_cache
            clear_cache()
        except:
            pass
        
        # Database connection pool cleanup
        try:
            from models import db
            db.engine.dispose()
        except:
            pass
        
        # Force garbage collection with all generations
        for generation in range(3):
            gc.collect(generation)
    
    def _log_request_performance(self):
        """Log slow requests"""
        if hasattr(g, 'request_start_time'):
            duration = time.time() - g.request_start_time
            if duration > 2.0:  # Log requests slower than 2 seconds
                logger.warning(
                    f"Slow request: {request.method} {request.path} took {duration:.2f}s"
                )

# Global cleanup manager
cleanup_manager = CleanupManager()

def init_cleanup_middleware(app):
    """Initialize cleanup middleware"""
    app.before_request(cleanup_manager.before_request)
    app.after_request(cleanup_manager.after_request)
    
    logger.info("Cleanup middleware initialized")
