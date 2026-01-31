"""
Debug Utilities - Conditional Debug Logging
Only logs when DEBUG mode is enabled via environment variable
"""
import os
import json
import time
import logging

logger = logging.getLogger(__name__)

# Check if debug mode is enabled
DEBUG_MODE = os.getenv('DEBUG', 'False').lower() == 'true'
DEBUG_LOG_PATH = os.getenv('DEBUG_LOG_PATH', '/tmp/debug.log')

def debug_log(location: str, message: str, data: dict = None, hypothesis_id: str = None):
    """
    Conditional debug logging - only logs when DEBUG mode is enabled
    
    Args:
        location: Code location (e.g., 'app.py:123')
        message: Log message
        data: Additional data to log
        hypothesis_id: Hypothesis ID for debugging
    """
    if not DEBUG_MODE:
        return
    
    try:
        log_entry = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": hypothesis_id or "DEBUG",
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000)
        }
        
        with open(DEBUG_LOG_PATH, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        # Silently fail - don't break production code
        logger.debug(f"Debug log failed: {e}")


def debug_fetch(endpoint: str, payload: dict):
    """
    Conditional debug fetch - only sends when DEBUG mode is enabled
    
    Args:
        endpoint: Debug endpoint URL
        payload: Payload to send
    """
    if not DEBUG_MODE:
        return
    
    try:
        import requests
        requests.post(
            endpoint,
            json=payload,
            timeout=0.1,  # Very short timeout - don't block
            headers={'Content-Type': 'application/json'}
        )
    except Exception:
        # Silently fail - don't break production code
        pass

