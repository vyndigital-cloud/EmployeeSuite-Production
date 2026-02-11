"""
Unified Error Boundary Decorator
NUCLEAR SPEC: Full stack traces with local variables for every error
"""

import sys
import traceback
import uuid
from functools import wraps
from flask import g, jsonify, request

try:
    from logging_config import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def generate_request_id():
    """Generate unique request ID for log correlation"""
    if not hasattr(g, 'request_id'):
        g.request_id = str(uuid.uuid4())[:8]  # Short ID for readability
    return g.request_id


def capture_local_variables(tb):
    """Capture local variables from traceback frames"""
    local_vars = {}
    while tb is not None:
        frame = tb.tb_frame
        frame_locals = {k: repr(v)[:200] for k, v in frame.f_locals.items()}  # Truncate long values
        local_vars[f"{frame.f_code.co_filename}:{tb.tb_lineno}"] = frame_locals
        tb = tb.tb_next
    return local_vars


def unified_error_boundary(f):
    """
    NUCLEAR SPEC: Unified error boundary that captures:
    - Full stack trace
    - Local variables at crash point
    - Request context (user, shop, endpoint)
    - Request ID for log correlation
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        request_id = generate_request_id()
        
        try:
            return f(*args, **kwargs)
        
        except Exception as e:
            # Capture full exception info
            exc_type, exc_value, exc_tb = sys.exc_info()
            
            # Get full stack trace
            stack_trace = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
            
            # Capture local variables from each frame
            local_vars = capture_local_variables(exc_tb)
            
            # Build comprehensive error context
            error_context = {
                'request_id': request_id,
                'endpoint': request.endpoint if request else 'UNKNOWN',
                'method': request.method if request else 'UNKNOWN',
                'url': request.url if request else 'UNKNOWN',
                'user_id': getattr(g, 'user_id', None),
                'shop_domain': getattr(g, 'shop_domain', request.args.get('shop') if request else None),
                'ip': request.headers.get('X-Forwarded-For', request.remote_addr) if request else None,
                'user_agent': request.headers.get('User-Agent') if request else None,
                'exception_type': exc_type.__name__,
                'exception_message': str(exc_value),
                'stack_trace': stack_trace,
                'local_variables': local_vars,
            }
            
            # CRITICAL log with full context
            logger.critical(
                f"🔥 CRITICAL ERROR | "
                f"Request ID: {request_id} | "
                f"Endpoint: {error_context['endpoint']} | "
                f"Shop: {error_context['shop_domain']} | "
                f"Exception: {error_context['exception_type']}: {error_context['exception_message']} | "
                f"URL: {error_context['url']} | "
                f"STACK_TRACE: {stack_trace} | "
                f"LOCAL_VARS: {local_vars}"
            )
            
            # Return 500 with request ID for correlation
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred',
                'request_id': request_id,
                'details': str(exc_value) if logger.level <= 10 else None  # Only in DEBUG mode
            }), 500
    
    return decorated_function


def require_jwt_strict(f):
    """
    NUCLEAR SPEC: JWT Kill-Switch
    Hard requirement for JWT verification - NO EXCEPTIONS
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        request_id = generate_request_id()
        
        # Check JWT verification status
        is_verified = getattr(request, 'session_token_verified', False)
        
        if not is_verified:
            shop = request.args.get('shop', 'UNKNOWN')
            
            # CRITICAL alert
            logger.critical(
                f"🚨 JWT KILL-SWITCH TRIGGERED | "
                f"Request ID: {request_id} | "
                f"Endpoint: {request.endpoint} | "
                f"Shop: {shop} | "
                f"URL: {request.url} | "
                f"IP: {request.headers.get('X-Forwarded-For', request.remote_addr)} | "
                f"User-Agent: {request.headers.get('User-Agent')}"
            )
            
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Valid session token required',
                'request_id': request_id
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function
