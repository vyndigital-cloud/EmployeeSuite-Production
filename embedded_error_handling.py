"""
Embedded App Error Handling - Shopify Best Practices
Implements proper error handling for embedded Shopify apps
"""
import logging
import traceback
from flask import jsonify, render_template_string, request, Response
from logging_config import logger

class EmbeddedAppError(Exception):
    """Base class for embedded app errors"""
    def __init__(self, message, error_code="EMBEDDED_ERROR", status_code=500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

class SessionTokenError(EmbeddedAppError):
    """Session token related errors"""
    def __init__(self, message="Invalid session token"):
        super().__init__(message, "SESSION_TOKEN_ERROR", 401)

class ShopifyAPIError(EmbeddedAppError):
    """Shopify API related errors"""
    def __init__(self, message="Shopify API error"):
        super().__init__(message, "SHOPIFY_API_ERROR", 502)

class PermissionError(EmbeddedAppError):
    """Permission related errors"""
    def __init__(self, message="Insufficient permissions"):
        super().__init__(message, "PERMISSION_ERROR", 403)

def create_error_response(error_code, message, status_code=500, details=None):
    """
    Create standardized error response for embedded apps
    """
    error_data = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": logger.info(f"Error occurred: {error_code} - {message}") or None
        }
    }
    
    if details:
        error_data["error"]["details"] = details
    
    # Add request context for debugging
    if request:
        error_data["error"]["request_info"] = {
            "path": request.path,
            "method": request.method,
            "is_embedded": bool(request.args.get('host')),
            "shop": request.args.get('shop')
        }
    
    return jsonify(error_data), status_code

def create_embedded_error_page(title, message, error_code=None, show_reload=True):
    """
    Create user-friendly error page for embedded apps
    """
    error_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title} - Employee Suite</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f6f6f7;
                margin: 0;
                padding: 40px 20px;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }}
            .error-container {{
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                padding: 40px;
                max-width: 500px;
                text-align: center;
            }}
            .error-icon {{
                font-size: 48px;
                margin-bottom: 16px;
            }}
            .error-title {{
                font-size: 20px;
                font-weight: 600;
                color: #202223;
                margin-bottom: 12px;
            }}
            .error-message {{
                font-size: 14px;
                color: #6d7175;
                line-height: 1.5;
                margin-bottom: 24px;
            }}
            .error-code {{
                font-size: 12px;
                color: #8c9196;
                font-family: monospace;
                background: #f6f6f7;
                padding: 4px 8px;
                border-radius: 4px;
                margin-bottom: 24px;
            }}
            .reload-btn {{
                background: #008060;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: background 0.15s;
            }}
            .reload-btn:hover {{
                background: #006e52;
            }}
        </style>
    </head>
    <body>
        <div class="error-container">
            <div class="error-icon">⚠️</div>
            <div class="error-title">{title}</div>
            <div class="error-message">{message}</div>
            {f'<div class="error-code">Error Code: {error_code}</div>' if error_code else ''}
            {f'<button class="reload-btn" onclick="reloadApp()">Reload App</button>' if show_reload else ''}
        </div>
        
        <script>
            function reloadApp() {{
                if (window.shopify && window.shopify.app) {{
                    // Use App Bridge to reload
                    window.shopify.app.dispatch(window.shopify.app.Action.RELOAD);
                }} else {{
                    // Fallback to page reload
                    window.location.reload();
                }}
            }}
            
            // Auto-reload after 30 seconds for temporary errors
            setTimeout(function() {{
                reloadApp();
            }}, 30000);
        </script>
    </body>
    </html>
    """
    
    return Response(error_html, status=500, mimetype='text/html')

def handle_embedded_error(error):
    """
    Handle errors in embedded app context
    Returns appropriate response based on request type
    """
    try:
        # Log the error
        logger.error(f"Embedded app error: {error}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Check if request is from embedded app
        is_embedded = bool(request.args.get('host'))
        
        # API request - return JSON error
        if request.path.startswith('/api/') or request.headers.get('Content-Type') == 'application/json':
            if isinstance(error, EmbeddedAppError):
                return create_error_response(
                    error.error_code,
                    error.message,
                    error.status_code
                )
            else:
                return create_error_response(
                    "INTERNAL_ERROR",
                    "An internal error occurred",
                    500
                )
        
        # Embedded request - return HTML error page
        elif is_embedded:
            if isinstance(error, SessionTokenError):
                return create_embedded_error_page(
                    "Authentication Required",
                    "Please refresh the page to continue.",
                    error.error_code
                )
            elif isinstance(error, PermissionError):
                return create_embedded_error_page(
                    "Access Denied",
                    "You don't have permission to access this feature.",
                    error.error_code
                )
            elif isinstance(error, ShopifyAPIError):
                return create_embedded_error_page(
                    "Shopify Error",
                    "Unable to connect to Shopify. Please try again.",
                    error.error_code
                )
            else:
                return create_embedded_error_page(
                    "Something Went Wrong",
                    "An unexpected error occurred. Please try again.",
                    "INTERNAL_ERROR"
                )
        
        # Standalone request - return simple error page
        else:
            return create_embedded_error_page(
                "Error",
                str(error),
                getattr(error, 'error_code', None)
            )
            
    except Exception as e:
        # Fallback error handling
        logger.critical(f"Error in error handler: {e}")
        return Response("Internal Server Error", status=500)

def safe_api_call(func, *args, **kwargs):
    """
    Wrapper for safe API calls with proper error handling
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"API call failed: {e}")
        raise ShopifyAPIError(f"API call failed: {str(e)}")

def validate_embedded_request():
    """
    Validate embedded app request
    Raises appropriate errors if validation fails
    """
    # Check if request is from embedded app
    if not request.args.get('host'):
        logger.warning("Request not from embedded app")
        return False
    
    # Check session token
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise SessionTokenError("Missing session token")
    
    # TODO: Add more validation as needed
    
    return True

def create_loading_overlay(message="Loading..."):
    """
    Create loading overlay for embedded apps
    """
    return f"""
    <div id="loading-overlay" style="
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.9);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    ">
        <div style="text-align: center;">
            <div style="
                width: 40px;
                height: 40px;
                border: 3px solid #e1e3e5;
                border-top: 3px solid #008060;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 16px;
            "></div>
            <div style="color: #6d7175; font-size: 14px;">{message}</div>
        </div>
        <style>
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </div>
    """

def show_loading_overlay():
    """
    Show loading overlay via JavaScript
    """
    return """
    <script>
        if (typeof document !== 'undefined') {
            document.body.insertAdjacentHTML('beforeend`, `""" + create_loading_overlay() + """`);
        }
    </script>
    """

def hide_loading_overlay():
    """
    Hide loading overlay via JavaScript
    """
    return """
    <script>
        if (typeof document !== 'undefined') {
            const overlay = document.getElementById('loading-overlay');
            if (overlay) {
                overlay.remove();
            }
        }
    </script>
    """

# Error handler decorator
def handle_errors(f):
    """
    Decorator to automatically handle errors in embedded app routes
    """
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return handle_embedded_error(e)
    
    return wrapper
