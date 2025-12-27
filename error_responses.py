"""
Standardized Error Response Utilities
Provides consistent error response structure across all API endpoints
"""
from flask import jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_error_response(
    message: str,
    code: str = None,
    status_code: int = 500,
    details: dict = None,
    action: str = None,
    action_url: str = None
) -> tuple:
    """
    Create a standardized error response
    
    Args:
        message: Human-readable error message
        code: Error code (e.g., 'AUTH_REQUIRED', 'PERMISSION_DENIED')
        status_code: HTTP status code (400, 401, 403, 404, 500, etc.)
        details: Additional error details (optional)
        action: Suggested action ('refresh', 'subscribe', 'install', 'retry')
        action_url: URL for the action (optional)
    
    Returns:
        Tuple of (JSON response, HTTP status code)
    
    Example:
        return create_error_response(
            message="Authentication required",
            code="AUTH_REQUIRED",
            status_code=401,
            action="login",
            action_url="/login"
        )
    """
    response = {
        'status': 'error',
        'code': code or f'ERROR_{status_code}',
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if details:
        response['details'] = details
    
    if action:
        response['action'] = action
        if action_url:
            response['action_url'] = action_url
    
    return jsonify(response), status_code


def create_success_response(
    message: str = None,
    data: dict = None,
    status_code: int = 200
) -> tuple:
    """
    Create a standardized success response
    
    Args:
        message: Success message (optional)
        data: Response data (optional)
        status_code: HTTP status code (default: 200)
    
    Returns:
        Tuple of (JSON response, HTTP status code)
    """
    response = {
        'status': 'success',
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if message:
        response['message'] = message
    
    if data:
        response['data'] = data
    
    return jsonify(response), status_code


# Common error responses
def auth_required(message: str = "Authentication required") -> tuple:
    """401 Unauthorized - User not authenticated"""
    return create_error_response(
        message=message,
        code='AUTH_REQUIRED',
        status_code=401,
        action='login',
        action_url='/login'
    )


def permission_denied(message: str = "Permission denied") -> tuple:
    """403 Forbidden - User lacks required permissions"""
    return create_error_response(
        message=message,
        code='PERMISSION_DENIED',
        status_code=403,
        action='subscribe',
        action_url='/billing/subscribe'
    )


def not_found(message: str = "Resource not found") -> tuple:
    """404 Not Found"""
    return create_error_response(
        message=message,
        code='NOT_FOUND',
        status_code=404
    )


def bad_request(message: str = "Bad request", details: dict = None) -> tuple:
    """400 Bad Request - Invalid input"""
    return create_error_response(
        message=message,
        code='BAD_REQUEST',
        status_code=400,
        details=details
    )


def server_error(message: str = "Internal server error", details: dict = None) -> tuple:
    """500 Internal Server Error"""
    # Log server errors
    logger.error(f"Server error: {message}", extra={'details': details})
    return create_error_response(
        message=message,
        code='SERVER_ERROR',
        status_code=500,
        details=details if details else None
    )


def rate_limit_exceeded(message: str = "Rate limit exceeded") -> tuple:
    """429 Too Many Requests"""
    return create_error_response(
        message=message,
        code='RATE_LIMIT_EXCEEDED',
        status_code=429,
        action='retry',
        details={'retry_after': 60}  # seconds
    )


def subscription_required(message: str = "Subscription required") -> tuple:
    """403 Forbidden - Subscription expired"""
    return create_error_response(
        message=message,
        code='SUBSCRIPTION_REQUIRED',
        status_code=403,
        action='subscribe',
        action_url='/billing/subscribe',
        details={'trial_ended': True}
    )

