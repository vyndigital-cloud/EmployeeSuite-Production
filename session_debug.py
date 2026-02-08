"""
Session Debugging Utility
Helps diagnose iframe session amnesia issues.

This utility logs detailed session information to help identify when
browsers are blocking cookies in iframe contexts.
"""

from flask import request, session
from logging_config import logger
import os


def log_session_state(context=""):
    """
    Log detailed session state for debugging.
    
    Args:
        context: Description of where this is being called from
    """
    try:
        # Session info
        session_id = session.get('_id', 'NO_SESSION_ID')
        user_id = session.get('_user_id', 'NO_USER')
        shop_domain = session.get('shop_domain', 'NO_SHOP')
        
        # Request info
        is_embedded = (
            request.args.get('shop') or 
            request.args.get('host') or 
            request.headers.get('X-Shopify-Shop-Domain')
        )
        
        # Cookie info
        cookies = request.cookies
        session_cookie = cookies.get('session', 'NO_SESSION_COOKIE')
        
        logger.info(f"🔍 SESSION DEBUG [{context}]:")
        logger.info(f"  - Session ID: {session_id}")
        logger.info(f"  - User ID: {user_id}")
        logger.info(f"  - Shop Domain: {shop_domain}")
        logger.info(f"  - Is Embedded: {bool(is_embedded)}")
        logger.info(f"  - Session Cookie Present: {session_cookie != 'NO_SESSION_COOKIE'}")
        logger.info(f"  - Session Keys: {list(session.keys())}")
        logger.info(f"  - Request Path: {request.path}")
        logger.info(f"  - Request Args: {dict(request.args)}")
        
        # Check for session amnesia indicators
        if user_id == 'NO_USER' and session_cookie != 'NO_SESSION_COOKIE':
            logger.warning("⚠️  SESSION AMNESIA: Cookie present but no user in session!")
        
        if is_embedded and session_cookie == 'NO_SESSION_COOKIE':
            logger.warning("⚠️  IFRAME COOKIE BLOCK: Embedded request but no session cookie!")
            
    except Exception as e:
        logger.error(f"Error logging session state: {e}")


def check_cookie_compatibility():
    """
    Check if the current request/response will support cookies.
    
    Returns:
        dict: Compatibility information
    """
    try:
        # Check if request is HTTPS (required for SameSite=None)
        is_https = request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
        
        # Check if embedded
        is_embedded = bool(
            request.args.get('shop') or 
            request.args.get('host') or 
            request.headers.get('X-Shopify-Shop-Domain')
        )
        
        # Check user agent for known problematic browsers
        user_agent = request.headers.get('User-Agent', '').lower()
        is_safari = 'safari' in user_agent and 'chrome' not in user_agent
        is_chrome = 'chrome' in user_agent
        
        compatibility = {
            'is_https': is_https,
            'is_embedded': is_embedded,
            'is_safari': is_safari,
            'is_chrome': is_chrome,
            'cookies_likely_blocked': is_embedded and not is_https,
            'samesite_none_supported': is_https,
        }
        
        if compatibility['cookies_likely_blocked']:
            logger.warning(
                "⚠️  COOKIE COMPATIBILITY WARNING: "
                "Embedded request without HTTPS - cookies will likely be blocked!"
            )
        
        if is_embedded and (is_safari or is_chrome):
            logger.info(
                f"ℹ️  Embedded request from {'Safari' if is_safari else 'Chrome'} - "
                "using SameSite=None cookies"
            )
        
        return compatibility
        
    except Exception as e:
        logger.error(f"Error checking cookie compatibility: {e}")
        return {}


def add_session_debug_headers(response):
    """
    Add debug headers to response to help diagnose session issues.
    
    Args:
        response: Flask response object
    
    Returns:
        Modified response object
    """
    try:
        # Only add debug headers in development
        if os.getenv('ENVIRONMENT') != 'production':
            response.headers['X-Session-Debug'] = 'enabled'
            response.headers['X-Session-User'] = str(session.get('_user_id', 'none'))
            response.headers['X-Session-Shop'] = str(session.get('shop_domain', 'none'))
            
    except Exception as e:
        logger.error(f"Error adding session debug headers: {e}")
    
    return response
