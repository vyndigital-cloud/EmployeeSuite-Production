import sys
import os
import signal
import traceback
import logging

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip

# Force single-threaded numpy/pandas operations to prevent segfaults
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

# CRITICAL: Set up detailed crash logging for debugging segfaults
# This will help us identify exactly where crashes occur
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True  # Override any existing config
)

# CRITICAL: Set signal handlers to prevent segfaults from crashing entire worker
# This catches SIGSEGV (segmentation fault) and logs it instead of crashing
def segfault_handler(signum, frame):
    """Handle segmentation faults gracefully"""
    import traceback
    from logging_config import logger
    logger.critical(f"Segmentation fault detected (signal {signum}) - attempting graceful recovery")
    logger.critical(f"Traceback: {''.join(traceback.format_stack(frame))}")
    # Don't exit - let the worker restart naturally
    # This prevents the entire process from crashing

# Only set handler if not in a subprocess (gunicorn workers are subprocesses)
# Setting signal handlers in workers can interfere with gunicorn's process management
if os.getpid() != 1:  # Not the main process (PID 1 is usually the main process)
    try:
        # Note: SIGSEGV handler may not work in all environments
        # Gunicorn handles worker crashes automatically
        pass
    except Exception:
        pass

from flask import Flask, jsonify, render_template_string, redirect, url_for, request, session, Response

# Comprehensive instrumentation helper
def log_event(location, message, data=None, hypothesis_id='GENERAL'):
    """Log event using proper logging framework"""
    try:
        import json
        import time
        log_entry = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000)
        }
        # Use logging framework instead of file writes
        logger.info(f"DEBUG_EVENT: {json.dumps(log_entry)}")
    except Exception as e:
        logger.error(f"Failed to log event: {e}")

def safe_redirect(url, shop=None, host=None):
    """
    Safe redirect that works in both embedded and standalone contexts.
    For embedded apps, uses window.top.location.href to break out of iframe.
    For standalone, uses regular Flask redirect.
    """
    # Check if we're in an embedded context
    is_embedded = bool(host) or bool(shop) or request.args.get('embedded') == '1'
    
    if is_embedded:
        # Embedded app - use window.top.location.href to break out of iframe
        redirect_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Redirecting...</title>
    <script>
        // Break out of iframe immediately
        if (window.top !== window.self) {{
            window.top.location.href = '{url}';
        }} else {{
            window.location.href = '{url}';
        }}
    </script>
    <noscript>
        <meta http-equiv="refresh" content="0;url={url}">
    </noscript>
</head>
<body>
    <p>Redirecting... <a href="{url}">Click here if not redirected</a></p>
</body>
</html>"""
        return Response(redirect_html, mimetype='text/html')
    else:
        # Standalone - use regular Flask redirect
        return redirect(url)
from flask_login import LoginManager, login_required, current_user, login_user
from flask_bcrypt import Bcrypt
import logging
from datetime import datetime

from models import db, User, ShopifyStore
from auth import auth_bp
from shopify_oauth import oauth_bp
from shopify_routes import shopify_bp
from billing import billing_bp
from admin_routes import admin_bp
from legal_routes import legal_bp
from faq_routes import faq_bp
from rate_limiter import init_limiter
from webhook_stripe import webhook_bp
from webhook_shopify import webhook_shopify_bp
from gdpr_compliance import gdpr_bp
from session_token_verification import verify_session_token
from order_processing import process_orders
from inventory import update_inventory
from reporting import generate_report

from logging_config import logger
from access_control import require_access
from security_enhancements import (
    add_security_headers, 
    MAX_REQUEST_SIZE,
    sanitize_input_enhanced,
    log_security_event,
    require_https
)
from performance import compress_response

# Initialize Sentry for error monitoring (if DSN is provided)
sentry_dsn = os.getenv('SENTRY_DSN')
if sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    
    # CRITICAL: Disable profiling and traces to prevent segfaults after responses
    # These features can cause crashes when sending data to Sentry after response is sent
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FlaskIntegration(),
            SqlalchemyIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
        ],
        traces_sample_rate=0.0,  # DISABLED - causes segfaults after responses
        profiles_sample_rate=0.0,  # DISABLED - causes segfaults after responses
        environment=os.getenv('ENVIRONMENT', 'production'),
        release=os.getenv('RELEASE_VERSION', '1.0.0'),
        before_send=lambda event, hint: event if os.getenv('ENVIRONMENT') != 'development' else None,  # Don't send in dev
        # CRITICAL: Disable background worker threads that can cause segfaults
        transport=sentry_sdk.transport.HttpTransport if hasattr(sentry_sdk, 'transport') else None,
    )
    logger.info("Sentry error monitoring initialized")
else:
    logger.warning("SENTRY_DSN not set - error monitoring disabled")

app = Flask(__name__, static_folder='static', template_folder='templates')
# SECRET_KEY is REQUIRED in production - fail fast if missing
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if os.getenv('ENVIRONMENT') == 'production' or os.getenv('FLASK_ENV') == 'production':
        raise ValueError("SECRET_KEY environment variable is REQUIRED in production. Set it in your deployment platform.")
    # Only allow dev secret in non-production environments
    SECRET_KEY = 'dev-secret-key-change-in-production'
    logger.warning("Using default SECRET_KEY - THIS IS INSECURE. Set SECRET_KEY environment variable.")
app.config['SECRET_KEY'] = SECRET_KEY
# ============================================================================
# SESSION COOKIE CONFIGURATION - 100% OPTIMIZED FOR EMBEDDED & STANDALONE
# ============================================================================
# CRITICAL: Embedded apps use session tokens (NO cookies needed)
# Standalone access uses cookies with optimal Safari/Chrome compatibility

# Base cookie settings - work for both embedded and standalone
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only (REQUIRED for SameSite=None)
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Required for cross-origin (embedded apps)
app.config['SESSION_COOKIE_DOMAIN'] = None  # Let browser handle domain (Safari compatibility)
app.config['SESSION_COOKIE_PATH'] = '/'  # Available site-wide
app.config['SESSION_COOKIE_NAME'] = 'session'  # Standard name

# Remember cookie settings - ONLY for standalone (not used in embedded mode)
app.config['REMEMBER_COOKIE_DURATION'] = 2592000  # 30 days
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'None'  # Same as session cookie
app.config['REMEMBER_COOKIE_SECURE'] = True  # HTTPS only
app.config['REMEMBER_COOKIE_DOMAIN'] = None  # Safari compatibility
app.config['REMEMBER_COOKIE_NAME'] = 'remember_token'  # Standard name

# Session lifetime - shorter for embedded apps (they use tokens anyway)
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours (embedded apps use tokens)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///employeesuite.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Performance optimizations - Optimized for speed
# Base engine options (work for all databases)
engine_options = {
    'pool_pre_ping': True,  # CRITICAL: Verify connections before using (prevents segfaults)
    'echo': False,  # Disable SQL logging for performance
}

# PostgreSQL-specific options
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql://'):
    engine_options.update({
        'pool_size': 2,  # Ultra-conservative to prevent connection exhaustion and segfaults
        'max_overflow': 3,  # Minimal overflow for stability
        'pool_recycle': 600,  # Recycle connections after 10 minutes (prevent stale connections)
        'pool_timeout': 5,  # Shorter timeout for getting connection from pool
        'connect_args': {
            'connect_timeout': 3,  # Fast connection timeout
            'options': '-c statement_timeout=20000'  # 20 second query timeout (prevent hangs)
        },
        'isolation_level': 'READ_COMMITTED',  # Prevent deadlocks
    })

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_options

db.init_app(app)

# ============================================================================
# COMPREHENSIVE ERROR LOGGING SYSTEM - Capture EVERY error crumb
# ============================================================================
from logging_config import log_comprehensive_error, logger

# Global error handler for ALL exceptions
@app.errorhandler(Exception)
def handle_all_exceptions(e):
    """Catch and log EVERY exception with full details"""
    from flask import request, jsonify
    import traceback
    import json
    import time
    
    error_type = type(e).__name__
    error_message = str(e)
    error_location = f"{request.endpoint or 'unknown'}:{request.method}"
    
    # #region agent log
    try:
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"app.py:handle_all_exceptions","message":"Python exception caught","data":{"error_type":error_type,"error_message":error_message[:200],"error_location":error_location,"url":request.url[:100],"method":request.method,"endpoint":request.endpoint or "unknown","stack_trace":traceback.format_exc()[:500]},"timestamp":int(time.time()*1000)})+'\n')
    except: pass
    # #endregion
    
    # Get full request context
    error_data = {
        'url': request.url,
        'method': request.method,
        'endpoint': request.endpoint,
        'args': dict(request.args),
        'form_data': dict(request.form) if request.form else None,
        'headers': dict(request.headers),
        'remote_addr': request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'referer': request.headers.get('Referer'),
    }
    
    # Log with full stack trace
    exc_info = sys.exc_info()
    log_comprehensive_error(error_type, error_message, error_location, error_data, exc_info)
    
    # Return appropriate response using standardized error format
    if request.path.startswith('/api/'):
        from error_responses import server_error
        return server_error(
            message="An unexpected error occurred",
            details={
                'error_type': error_type,
                'location': error_location
            }
        )
    else:
        # For non-API requests, return user-friendly HTML error
        # Don't expose stack trace in production
        if os.getenv('ENVIRONMENT') == 'production':
            return f"<h1>Error</h1><p>An error occurred. Please try again or contact support.</p>", 500
        else:
            return f"<h1>Error: {error_message}</h1><pre>{traceback.format_exc()}</pre>", 500

# Specific error handlers for common error types
@app.errorhandler(404)
def handle_404(e):
    """Log 404 errors with full context - Enhanced per external feedback"""
    from flask import request
    import logging
    
    # Enhanced error data with all possible context
    error_data = {
        'url': request.url,
        'path': request.path,
        'full_path': request.full_path,
        'method': request.method,
        'endpoint': request.endpoint or 'unknown',
        'referer': request.headers.get('Referer'),
        'user_agent': request.headers.get('User-Agent'),
        'remote_addr': request.remote_addr,
        'args': dict(request.args),
        'form_data': dict(request.form) if request.form else None,
        'is_api_request': request.path.startswith('/api/'),
        'is_static': request.path.startswith('/static/'),
    }
    
    # Log to both comprehensive error system and standard logging
    location = f"{request.endpoint or 'unknown'}:{request.method}"
    log_comprehensive_error('HTTP_404', str(e), location, error_data)
    
    # Also log to standard logger with full details (per external feedback)
    logger.error(f"404 error occurred: {request.method} {request.path}")
    logger.error(f"Full URL: {request.url}")
    logger.error(f"Referer: {request.headers.get('Referer', 'None')}")
    logger.error(f"User-Agent: {request.headers.get('User-Agent', 'None')}")
    logger.error(f"Requested endpoint: {request.endpoint or 'unknown'}")
    
    # Return appropriate response based on request type
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found', 'path': request.path, 'method': request.method}), 404
    
    # For non-API requests, let the second handler (not_found) handle HTML response
    # This prevents duplicate handler conflicts
    pass  # Will fall through to not_found handler

@app.errorhandler(500)
def handle_500(e):
    """Log all 500 internal server errors with stack trace (per external feedback)"""
    from flask import request
    import traceback
    import logging
    
    error_data = {
        'url': request.url,
        'method': request.method,
        'endpoint': request.endpoint,
        'args': dict(request.args),
        'path': request.path,
        'referer': request.headers.get('Referer'),
        'user_agent': request.headers.get('User-Agent'),
    }
    
    # Get full stack trace
    exc_info = sys.exc_info()
    stack_trace = ''.join(traceback.format_exception(*exc_info)) if exc_info[0] else traceback.format_exc()
    
    # Log to comprehensive error system
    log_comprehensive_error('500', str(e), f"{request.endpoint or 'unknown'}:{request.method}", error_data, exc_info)
    
    # Also log to standard logger with full details (per external feedback)
    logger.error(f"500 Error: {e}, Path: {request.path}")
    logger.error(f"Full URL: {request.url}")
    logger.error(f"Stack trace:\n{stack_trace}")
    
    # Return user-friendly error message
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error': 'An internal server error occurred. Please try again later.',
            'error_type': 'InternalServerError'
        }), 500
    
    return str(e), 500

@app.errorhandler(400)
def handle_400(e):
    """Log 400 errors with full context"""
    from flask import request
    error_data = {
        'url': request.url,
        'method': request.method,
        'args': dict(request.args),
        'form_data': dict(request.form) if request.form else None,
    }
    log_comprehensive_error('400', str(e), f"{request.endpoint or 'unknown'}:{request.method}", error_data)
    return str(e), 400

# Database error handler - catch before general handler
from sqlalchemy.exc import SQLAlchemyError

def handle_database_error_specifically(e):
    """Specifically catch database errors with detailed logging"""
    if isinstance(e, SQLAlchemyError):
        from flask import request
        error_data = {
            'url': request.url,
            'method': request.method,
            'database_error': True,
            'error_code': getattr(e, 'code', None),
            'statement': getattr(e, 'statement', None),
            'params': getattr(e, 'params', None),
        }
        exc_info = sys.exc_info()
        log_comprehensive_error('DatabaseError', str(e), f"{request.endpoint or 'unknown'}:{request.method}", error_data, exc_info)

# After request handler to log all responses
@app.after_request
def log_response(response):
    """Log all responses, especially errors"""
    if response.status_code >= 400:
        from flask import request
        error_data = {
            'status_code': response.status_code,
            'url': request.url,
            'method': request.method,
            'response_size': len(response.get_data()),
        }
        log_comprehensive_error(
            f'HTTP_{response.status_code}',
            f"HTTP {response.status_code} response",
            f"{request.endpoint or 'unknown'}:{request.method}",
            error_data
        )
    return response

# ============================================================================
# END COMPREHENSIVE ERROR LOGGING SYSTEM
# ============================================================================

# Configure server-side sessions - optimized for embedded and standalone
app.config['SESSION_PERMANENT'] = True
# Session lifetime is already set above (24 hours)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    # CRITICAL: Protect against segfaults from corrupted connections
    # DO NOT call db.session.remove() before query - pool_pre_ping handle validation
    # CRITICAL: Do NOT call db.session.remove() in finally - causes segfaults
    try:
        return User.query.get(int(user_id))
    except BaseException:
        # Catch segfault precursors - return None to let Flask-Login handle it
        try:
            db.session.rollback()
        except Exception:
            pass
        # Removed db.session.remove() from finally - causes segfaults
        return None

@login_manager.unauthorized_handler
def unauthorized():
    """Handle unauthorized access - redirect embedded apps to OAuth, standalone to login"""
    from flask import request, redirect, url_for, has_request_context
    # CRITICAL: Only use request context if we're in a request
    if not has_request_context():
        # Not in a request context - return a simple redirect
        return redirect('/login')
    
    # Check if this is an embedded app request
    shop = request.args.get('shop')
    embedded = request.args.get('embedded')
    host = request.args.get('host')
    
    # CRITICAL: For embedded apps, redirect to OAuth (Shopify's embedded auth flow)
    # DO NOT redirect to login form - embedded apps use OAuth
    if embedded == '1' or (shop and host):
        if shop:
            install_url = url_for('oauth.install', shop=shop, host=host) if host else url_for('oauth.install', shop=shop)
            logger.info(f"Unauthorized embedded app request - redirecting to OAuth via install route: {install_url}")
            return safe_redirect(install_url, shop=shop, host=host)
    
    # For standalone access, redirect to login form
    return redirect(url_for('auth.login'))

app.register_blueprint(auth_bp)
app.register_blueprint(shopify_bp)
app.register_blueprint(billing_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(legal_bp)
app.register_blueprint(oauth_bp)
app.register_blueprint(faq_bp)
app.register_blueprint(webhook_bp)
app.register_blueprint(webhook_shopify_bp)
app.register_blueprint(gdpr_bp)

# Initialize rate limiter with global 1000 req/hour (increased from 200 to allow legitimate usage)
limiter = init_limiter(app)

# Apply security headers and compression to all responses
@app.after_request
def optimize_response(response):
    """Add security headers, compress responses, and optimize cookies"""
    # CRITICAL: Wrap all operations in try/except to prevent segfaults after response
    try:
        from flask import has_request_context
        response = add_security_headers(response)
        # CRITICAL: Wrap compression in try/except - it can cause segfaults
        try:
            response = compress_response(response)
        except Exception as e:
            # If compression fails, return uncompressed response
            logger.debug(f"Compression failed (non-critical): {e}")
        
        # CRITICAL: Force session cookie to be set for Safari compatibility
        # Safari requires explicit cookie setting in response headers
        # Only access session if we're in a request context
        if has_request_context():
            try:
                # Check if session has been modified or is permanent
                if session.get('_permanent') or session.modified:
                    # Ensure cookie is set
                    session.modified = True
            except (RuntimeError, AttributeError):
                # Session not available in this context (webhook requests, etc.)
                pass
        
        # Enable Keep-Alive for webhook endpoints (Shopify requirement)
        # This allows Shopify to reuse connections, reducing latency
        if has_request_context():
            try:
                if request.path.startswith('/webhooks/'):
                    response.headers['Connection'] = 'keep-alive'
                    response.headers['Keep-Alive'] = 'timeout=5, max=1000'
                
                # Add cache headers for static assets
                if request.endpoint == 'static':
                    response.cache_control.max_age = 31536000  # 1 year
                    response.cache_control.public = True
            except Exception as e:
                # Non-critical - headers might not be accessible
                logger.debug(f"Header setting failed (non-critical): {e}")
    except Exception as e:
        # CRITICAL: Never let after_request crash - response already sent
        logger.error(f"Error in after_request handler (non-critical): {e}", exc_info=True)
    
    return response

# CRITICAL: Proper database session cleanup after each request
# This prevents connection pool exhaustion and segfaults (code 139)
@app.teardown_appcontext
def close_db(error):
    """Close database session after each request - prevents connection leaks and segfaults"""
    # CRITICAL: Wrap ALL operations in try/except - this runs AFTER response is sent
    # Any crashes here cause segfaults (code 139) because response is already sent
    from models import db
    try:
        # CRITICAL: Check if session exists and is bound before removing
        # This prevents segfaults from trying to remove a corrupted session
        try:
            # Check if session is bound (has a connection)
            if db.session.is_active:
                # Only remove if session is active - prevents segfaults from corrupted connections
                db.session.remove()
        except (AttributeError, RuntimeError, Exception) as e:
            # Non-critical - session might already be removed or connection is corrupted
            # Silently ignore to prevent segfaults
            pass
        
        # CRITICAL: Disable garbage collection in teardown - it can cause segfaults
        # Let Python's automatic GC handle it instead
        # if error:
        #     import gc
        #     gc.collect()  # DISABLED - causes segfaults after response
    except BaseException as e:
        # Catch ALL exceptions including segfault precursors (SystemExit, KeyboardInterrupt, etc.)
        # CRITICAL: Never let teardown crash - response already sent
        # Silently ignore all errors to prevent segfaults
        pass
        logger.debug(f"Teardown error handled (non-critical): {type(e).__name__}")
    # CRITICAL: Do NOT access request or response here
    # This function is called during app context teardown, which can happen outside requests
    # Request/response handling should be done in after_request handler instead

# Request validation before processing (optimized - fast checks only)
@app.before_request
def validate_request_security():
    """Validate incoming requests for security - minimal checks only"""
    # Global request logging (per external feedback)
    logger.info(f'Making request to: {request.path}, Method: {request.method}')
    
    # Skip database initialization for health checks (used by Render for deployment verification)
    # Skip validation for static files, health checks
    if request.endpoint in ('static', 'health') or request.endpoint is None:
        return
    
    # Ensure database is initialized (lazy initialization - non-blocking)
    # Only initialize on actual requests, not health checks
    ensure_db_initialized()
    
    
    # Skip for webhook endpoints (they have HMAC verification)
    # Note: Both /webhook/ (singular) and /webhooks/ (plural) are used
    if request.path.startswith('/webhook/') or request.path.startswith('/webhooks/'):
        return
    
    # Skip for billing endpoints (Stripe handles security)
    if request.path.startswith('/billing/') or request.path in ('/subscribe', '/create-checkout-session'):
        return
    
    # Skip for OAuth callbacks (Shopify handles security)
    if request.path.startswith('/auth/callback') or request.path.startswith('/install'):
        return
    
    # Skip for API endpoints (they have their own auth)
    if request.path.startswith('/api/'):
        return
    
    # Skip for export endpoints (they have their own auth)
    if request.path.startswith('/api/export/'):
        return
    
    # Only check request size for POST/PUT requests (not GET)
    if request.method in ('POST', 'PUT') and request.content_length and request.content_length > MAX_REQUEST_SIZE:
        log_security_event('request_too_large', f"IP: {request.remote_addr}, Size: {request.content_length}", 'WARNING')
        return jsonify({'error': 'Request too large'}), 413

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta charset="utf-8">
    <!-- Critical: Prevent any blocking - render immediately -->
    <style>
        /* Inline critical CSS - no blocking */
        body { margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    </style>
    <!-- Defer non-critical resources -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <!-- Shopify Polaris CSS - only load in embedded mode -->
    <script>
        // App Bridge CSS removed - it's optional and the file doesn't exist at the CDN URL
        // App Bridge JavaScript provides all necessary functionality without CSS
    </script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f6f6f7;
            color: #202223;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            min-height: 100vh;
            line-height: 1.5;
            margin: 0;
            padding: 0;
        }
        
        html {
            margin: 0;
            padding: 0;
            height: 100%;
        }
        
        /* Header - Hide in embedded mode (Shopify provides navigation) */
        .header {
            background: #ffffff;
            border-bottom: 1px solid #e1e3e5;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        /* Hide header when embedded - Shopify admin has its own nav */
        body.embedded .header {
            display: none !important;
        }
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
            height: 64px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo {
            font-size: 16px;
            font-weight: 600;
            color: #202223;
            text-decoration: none;
            letter-spacing: -0.2px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .header-nav {
            display: flex;
            gap: 4px;
            align-items: center;
        }
        .nav-btn {
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            color: #6d7175;
            transition: background 0.15s;
        }
        .nav-btn:hover {
            background: #f6f6f7;
            color: #202223;
        }
        .nav-btn-primary {
            background: #008060;
            color: #fff !important;
            transition: background 0.2s ease;
        }
        .nav-btn-primary:hover {
            background: #006e52;
            color: #fff !important;
        }
        
        /* Container - Shopify Spacing */
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 32px 24px;
        }
        
        /* Adjust container padding for embedded mode */
        body.embedded .container {
            padding: 20px 24px;
        }
        
        /* Remove footer in embedded mode */
        body.embedded footer {
            display: none !important;
        }
        
        /* Clean up body background for embedded */
        body.embedded {
            background: #ffffff;
        }
        
        .page-title {
            font-size: 32px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 8px;
            letter-spacing: -0.3px;
        }
        .page-subtitle {
            font-size: 15px;
            color: #6d7175;
            margin-bottom: 32px;
            font-weight: 400;
            line-height: 1.5;
            max-width: 600px;
        }
        
        /* Banner - Shopify Style */
        .banner {
            background: #ffffff;
            border: 1px solid #e1e3e5;
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .banner-warning {
            background: #fffbf0;
            border-color: #fef3c7;
        }
        .banner-info {
            background: #f0f4ff;
            border-color: #dbeafe;
        }
        .banner-content h3 {
            font-size: 15px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 4px;
        }
        .banner-content p {
            font-size: 14px;
            color: #6d7175;
            font-weight: 400;
        }
        .banner-action {
            background: #008060;
            color: #fff;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            white-space: nowrap;
            transition: background 0.15s;
        }
        .banner-action:hover {
            background: #006e52;
        }
        
        /* Cards Grid - Shopify Style */
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }
        .card {
            background: #ffffff;
            border: 1px solid #e1e3e5;
            border-radius: 8px;
            padding: 24px;
            transition: box-shadow 0.15s;
        }
        
        .card:hover {
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }
        
        .card-icon {
            font-size: 32px;
            margin-bottom: 16px;
            line-height: 1;
            display: inline-block;
        }
        
        .card-title {
            font-size: 17px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 8px;
            letter-spacing: -0.2px;
        }
        .card-description {
            font-size: 14px;
            color: #6d7175;
            line-height: 1.5;
            margin-bottom: 20px;
            font-weight: 400;
        }
        .card-btn {
            width: 100%;
            background: #008060;
            color: #fff;
            border: none;
            padding: 10px 16px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.15s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        
        .card-btn:hover {
            background: #006e52;
        }
        
        .card-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            background: #6d7175;
        }
        
        /* Output - Shopify Style */
        .output-container {
            background: #ffffff;
            border: 1px solid #e1e3e5;
            border-radius: 8px;
            overflow: hidden;
        }
        .output-header {
            padding: 16px 20px;
            border-bottom: 1px solid #e1e3e5;
            font-size: 14px;
            font-weight: 600;
            color: #202223;
            background: #f6f6f7;
        }
        #output {
            padding: 20px;
            min-height: 200px;
            font-size: 14px;
            line-height: 1.6;
            color: #6d7175;
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
        }
        #output:empty:before {
            content: 'Click any button above to get started. Your results will appear here.';
            color: #8c9196;
            font-style: italic;
            text-align: center;
            padding: 40px 20px;
            display: block;
        }
        #output:empty {
            display: flex;
            align-items: center;
            justify-content: center;
            background: #fafafa;
        }
        
        /* Loading - Shopify Style */
        .loading {
            text-align: center;
            padding: 48px 40px;
        }
        .spinner {
            width: 24px;
            height: 24px;
            border: 2px solid #e1e3e5;
            border-top: 2px solid #008060;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 12px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        @keyframes success {
            0% { transform: scale(0.8); opacity: 0; }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); opacity: 1; }
        }
        .loading-text {
            font-size: 14px;
            font-weight: 400;
            color: #6d7175;
        }
        
        /* Status */
        .success { color: #008060; font-weight: 500; }
        .error { color: #d72c0d; font-weight: 500; }
        
        /* Focus states */
        button:focus-visible,
        a:focus-visible {
            outline: 2px solid #008060;
            outline-offset: 2px;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .container { padding: 24px 16px; }
            .page-title { font-size: 24px; }
            .page-subtitle { font-size: 14px; margin-bottom: 24px; }
            .cards-grid { grid-template-columns: 1fr; gap: 16px; }
            .banner { flex-direction: column; gap: 16px; padding: 16px; }
            .banner-action { width: 100%; }
            .header-content { padding: 0 16px; height: 56px; }
            .card { padding: 20px; }
            #output { padding: 16px; }
        }
        @media (max-width: 480px) {
            .container { padding: 20px 12px; }
            .page-title { font-size: 20px; }
            .header-content { padding: 0 12px; }
        }
    </style>

    <!-- Shopify App Bridge - SIMPLE & RELIABLE -->
    <script>
        (function() {
            var urlParams = new URLSearchParams(window.location.search);
            var host = urlParams.get('host');
            var shop = urlParams.get('shop');
            
            // Global flag to track App Bridge readiness
            window.appBridgeReady = false;
            window.isEmbedded = !!host;
            
            // PERFECTED: Promise-based App Bridge ready system
            window.appBridgeReadyPromise = new Promise(function(resolve, reject) {
                window.appBridgeReadyResolve = resolve;
                window.appBridgeReadyReject = reject;
            });
            window.waitForAppBridge = function() {
                return window.appBridgeReadyPromise;
            };
            
            // Add embedded class to body for CSS targeting
            if (window.isEmbedded && document.body) {
                document.body.classList.add('embedded');
            }
            
            // Only load if we have host (embedded mode)
            if (!host) {
                window.shopifyApp = null;
                window.appBridgeReady = true; // Not embedded, so "ready" (won't use it)
                return;
            }
            
            // Load App Bridge - use App Bridge v3 CDN
            console.log('🔄 Loading App Bridge from CDN...');
            console.log('🔍 Debug info:', {host: host ? 'present' : 'missing', shop: shop ? 'present' : 'missing'});
            
            var script = document.createElement('script');
            script.src = 'https://cdn.shopify.com/shopifycloud/app-bridge.js';
            // Note: Not using async to ensure proper Safari compatibility
            
            // Safari-compatible App Bridge initialization
            // Safari doesn't immediately expose CDN script globals in onload callback
            // The 100ms timeout lets Safari's JS engine finish making the objects available
            script.onload = function() {
                console.log('✅ App Bridge script loaded successfully');
                // Give Safari a moment to make the objects available
                setTimeout(function() {
                    try {
                        if (window['app-bridge']) {
                            var createApp = window['app-bridge'].default;
                            
                            // Get API key from template
                            var apiKey = '{{ SHOPIFY_API_KEY or "" }}'.trim();
                            if (!apiKey || apiKey === '') {
                                apiKey = window.SHOPIFY_API_KEY || '';
                            }
                            
                            // Validate required parameters
                            if (!apiKey || apiKey === '') {
                                console.error('❌ SHOPIFY_API_KEY is missing - App Bridge cannot initialize');
                                window.shopifyApp = null;
                                window.appBridgeReady = true;
                                showAppBridgeError('Configuration Error: SHOPIFY_API_KEY environment variable is not set.');
                                return;
                            }
                            
                            if (!host || host === '' || host.trim() === '') {
                                console.error('❌ Host parameter is missing - App Bridge cannot initialize');
                                window.shopifyApp = null;
                                window.appBridgeReady = true;
                                showAppBridgeError('Configuration Error: Missing host parameter.');
                                return;
                            }
                            
                            // Initialize App Bridge
                                    window.shopifyApp = createApp({
                                apiKey: apiKey,
                                host: host
                            });
                            
                                    console.log('✅ App Bridge initialized successfully!');
                                    window.appBridgeReady = true;
                                    
                                    // Resolve Promise
                                    if (window.appBridgeReadyResolve) {
                                        window.appBridgeReadyResolve({
                                            ready: true,
                                            embedded: true,
                                            app: window.shopifyApp
                                        });
                                    }
                                    
                                    // Dispatch event
                                    window.dispatchEvent(new CustomEvent('appbridge:ready', {
                                        detail: { app: window.shopifyApp, embedded: true }
                                    }));
                                    
                                    // Enable buttons now that App Bridge is ready
                                    enableEmbeddedButtons();
                            } else {
                            // #region agent log
                            try {
                                fetch('http://127.0.0.1:7242/ingest/98f7b8ce-f573-4ca3-b4d4-0fb2bf283c8d',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'app.py:AppBridge:simple_failed','message':'App Bridge object not found after Safari delay','data':{'has_app_bridge':!!window['app-bridge'],'window_keys':Object.keys(window).filter(k => k.toLowerCase().includes('app') || k.toLowerCase().includes('bridge') || k.toLowerCase().includes('shopify')).slice(0,20),'user_agent':navigator.userAgent.substring(0,50),'script_src':script.src},"timestamp":Date.now(),sessionId:'debug-session',runId:'app-bridge-debug',hypothesisId:'F'})}).catch(()=>{});
                            } catch(e) {}
                            // #endregion
                            console.error('❌ App Bridge object not found after Safari delay');
                                window.shopifyApp = null;
                                window.appBridgeReady = true;
                            showAppBridgeError('App Bridge script loaded but object not found. Please refresh the page.');
                            }
                        } catch (e) {
                        console.error('❌ App Bridge initialization error:', e);
                            window.shopifyApp = null;
                            window.appBridgeReady = true;
                        showAppBridgeError('App Bridge error: ' + (e.message || 'Unknown error'));
                    }
                }, 100); // Safari needs this delay
            };
            
            script.onerror = function(error) {
                console.error('❌ Failed to load App Bridge script from CDN');
                console.error('Error details:', error);
                console.error('Script URL:', script.src);
                // #region agent log - App Bridge script load error
                try {
                    fetch('http://127.0.0.1:7242/ingest/98f7b8ce-f573-4ca3-b4d4-0fb2bf283c8d',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'app.py:appBridge:scriptError','message':'App Bridge script failed to load','data':{'scriptSrc':script.src,'hasHost':!!host,'hasShop':!!shop},"timestamp":Date.now(),sessionId:'debug-session',runId:'app-bridge-debug',hypothesisId:'H'})}).catch(()=>{});
                } catch(e) {}
                // #endregion
                
                // Try alternative CDN URL
                console.log('🔄 Trying alternative CDN URL...');
                var fallbackScript = document.createElement('script');
                fallbackScript.src = 'https://cdn.shopify.com/shopifycloud/app-bridge.js';
                fallbackScript.onload = function() {
                    console.log('✅ App Bridge loaded from fallback URL');
                    // Safari-compatible: Give Safari a moment to make objects available
                    setTimeout(function() {
                        if (window['app-bridge']) {
                            try {
                                var createApp = window['app-bridge'].default;
                                var apiKey = '{{ SHOPIFY_API_KEY or "" }}'.trim();
                                if (!apiKey || apiKey === '') {
                                    apiKey = window.SHOPIFY_API_KEY || '';
                                }
                                
                                if (apiKey && host) {
                                    window.shopifyApp = createApp({
                                        apiKey: apiKey,
                                        host: host
                                    });
                                    window.appBridgeReady = true;
                                    console.log('✅ App Bridge initialized from fallback');
                                    if (window.appBridgeReadyResolve) {
                                        window.appBridgeReadyResolve({
                                            ready: true,
                                            embedded: true,
                                            app: window.shopifyApp
                                        });
                                    }
                                    enableEmbeddedButtons();
                                } else {
                                    console.error('❌ Missing API key or host in fallback');
                                    window.shopifyApp = null;
                                    window.appBridgeReady = true;
                                    showAppBridgeError('Configuration Error: Missing API key or host parameter.');
                                }
                            } catch (e) {
                                console.error('❌ Fallback init error:', e);
                                window.shopifyApp = null;
                                window.appBridgeReady = true;
                                showAppBridgeError('Initialization Error: ' + (e.message || 'Unknown error') + '. Please refresh the page.');
                            }
                        } else {
                            // #region agent log
                            try {
                                fetch('http://127.0.0.1:7242/ingest/98f7b8ce-f573-4ca3-b4d4-0fb2bf283c8d',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'app.py:AppBridge:fallback_failed','message':'App Bridge not available after fallback load','data':{'has_app_bridge':!!window['app-bridge'],'window_keys':Object.keys(window).filter(k => k.toLowerCase().includes('app') || k.toLowerCase().includes('bridge') || k.toLowerCase().includes('shopify')).slice(0,20),'user_agent':navigator.userAgent.substring(0,50)},"timestamp":Date.now(),sessionId:'debug-session',runId:'app-bridge-debug',hypothesisId:'F'})}).catch(()=>{});
                            } catch(e) {}
                            // #endregion
                            console.error('❌ App Bridge not available even after fallback load');
                            window.shopifyApp = null;
                            window.appBridgeReady = true;
                            showAppBridgeError('Failed to load App Bridge. Please check your internet connection and refresh the page.');
                        }
                    }, 100); // Safari needs this delay
                };
                fallbackScript.onerror = function() {
                    console.error('❌ Fallback App Bridge script also failed');
                    window.shopifyApp = null;
                    window.appBridgeReady = true;
                    showAppBridgeError('Network Error: Unable to load App Bridge script. Please check your internet connection and try refreshing the page.');
                };
                document.head.appendChild(fallbackScript);
            };
            
            document.head.appendChild(script);
            
            // Helper function to show App Bridge errors
            function showAppBridgeError(message) {
                var output = document.getElementById('output');
                if (output) {
                    output.innerHTML = '<div style="padding: 20px; background: #fff4f4; border: 1px solid #fecaca; border-radius: 8px; color: #d72c0d;"><strong>App Bridge Error:</strong><br>' + message + '</div>';
                }
            }
            
            // Helper function to enable buttons after App Bridge is ready
            function enableEmbeddedButtons() {
                // Buttons are enabled by default, but we can add visual feedback
                console.log('✅ Embedded app ready - buttons enabled');
            }
        })();
    </script>
    
    <!-- Google Analytics - Load after page renders -->
    <script>
        // Defer analytics loading - wrapped to silently fail in iframes
        window.addEventListener('load', function() {
            try {
            var script = document.createElement('script');
            script.async = true;
            script.src = 'https://www.googletagmanager.com/gtag/js?id=G-RBBQ4X7FJ3';
            document.head.appendChild(script);
            
            script.onload = function() {
                    try {
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', 'G-RBBQ4X7FJ3');
                    } catch (e) {
                        // GA blocked in iframe - suppress error silently
                    }
                };
                
                script.onerror = function() {
                    // GA script failed to load (likely blocked in iframe) - suppress error
                };
            } catch (e) {
                // GA initialization failed - suppress error silently
            }
        });
    </script>
    
    <!-- Meta tags for better SEO and sharing -->
    <meta name="description" content="Monitor your Shopify store operations with order tracking, inventory management, and revenue analytics.">
    <meta name="keywords" content="shopify, automation, inventory, orders, analytics, ecommerce">
    <meta property="og:title" content="Employee Suite - Shopify Automation Platform">
    <meta property="og:description" content="Automate order processing, inventory management, and revenue reporting for your Shopify store.">
    <meta property="og:type" content="website">
    </head>
<body>
    <div class="header">
        <div class="header-content">
            <a href="/dashboard" style="text-decoration: none; color: inherit; display: flex; align-items: center; gap: 10px; font-weight: 600;" class="logo">
                <span>Employee Suite</span>
            </a>
            <div class="header-nav">
                <a href="/settings/shopify{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" class="nav-btn">Settings</a>
                <a href="{% if host %}{{ APP_URL }}/subscribe?shop={{ shop }}&host={{ host }}{% else %}{{ url_for('billing.subscribe') }}{% if shop %}?shop={{ shop }}{% endif %}{% endif %}" class="nav-btn nav-btn-primary">Subscribe</a>
                <a href="/logout" class="nav-btn">Logout</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px; flex-wrap: wrap; gap: 16px;">
            <div>
                <div class="page-title">Dashboard</div>
                <div class="page-subtitle">Monitor your Shopify store operations with inventory tracking, order monitoring, and comprehensive revenue analytics. 7-day free trial, no setup fees.</div>
            </div>
            {% if is_subscribed %}
            <div style="background: #fff; border: 1px solid #e5e5e5; border-radius: 16px; padding: 16px 20px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05); text-align: center; min-width: 140px;">
                <div style="font-size: 11px; color: #737373; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Subscribed</div>
                <div style="font-size: 20px; font-weight: 700; color: #0a0a0a;">✓ Active</div>
            </div>
            {% endif %}
        </div>
        
        {% if not has_access %}
        <div class="banner banner-warning" style="justify-content: space-between; align-items: center;">
            <div class="banner-content">
                <h3>Subscription Required</h3>
                <p>Your trial has ended. Subscribe now to continue using Employee Suite.</p>
            </div>
            <a href="{% if host %}{{ APP_URL }}/subscribe?shop={{ shop }}&host={{ host }}{% else %}{{ url_for('billing.subscribe') }}{% if shop %}?shop={{ shop }}{% endif %}{% endif %}" class="banner-action">Subscribe Now</a>
        </div>
        {% elif trial_active and not is_subscribed %}
        <div class="banner banner-warning" style="justify-content: space-between; align-items: center;">
            <div class="banner-content">
                <h3>⏰ Trial Active - {{ days_left }} day{{ 's' if days_left != 1 else '' }} remaining</h3>
                <p>Subscribe now to keep access when your trial ends. No credit card required until trial ends.</p>
            </div>
            <a href="{{ url_for('billing.subscribe') }}" class="banner-action">Subscribe Now →</a>
        </div>
        {% endif %}
        
        
        {% if has_shopify and quick_stats.has_data and is_subscribed %}
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; animation: fadeIn 0.5s ease-in;">
            <div style="background: linear-gradient(135deg, #fff 0%, #fafafa 100%); border: 1px solid #e5e5e5; border-radius: 16px; padding: 24px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); transition: all 0.3s ease;">
                <div style="font-size: 13px; color: #737373; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
                    <span>📦</span>
                    <span>Pending Orders</span>
                </div>
                <div style="font-size: 40px; font-weight: 800; color: #0a0a0a; line-height: 1; margin-bottom: 8px;">{{ quick_stats.pending_orders or 0 }}</div>
                <div style="font-size: 13px; color: #737373;">Need your attention</div>
            </div>
            <div style="background: linear-gradient(135deg, #fff 0%, #fafafa 100%); border: 1px solid #e5e5e5; border-radius: 16px; padding: 24px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); transition: all 0.3s ease;">
                <div style="font-size: 13px; color: #737373; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
                    <span>📊</span>
                    <span>Total Products</span>
                </div>
                <div style="font-size: 40px; font-weight: 800; color: #0a0a0a; line-height: 1; margin-bottom: 8px;">{{ quick_stats.total_products or 0 }}</div>
                <div style="font-size: 13px; color: #737373;">In your store</div>
            </div>
            <div style="background: linear-gradient(135deg, #fff 0%, #fafafa 100%); border: 1px solid #e5e5e5; border-radius: 16px; padding: 24px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); transition: all 0.3s ease;">
                <div style="font-size: 13px; color: #737373; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
                    <span>⚠️</span>
                    <span>Low Stock</span>
                </div>
                <div style="font-size: 40px; font-weight: 800; color: {% if quick_stats.low_stock_items > 0 %}#dc2626{% else %}#16a34a{% endif %}; line-height: 1; margin-bottom: 8px;">{{ quick_stats.low_stock_items or 0 }}</div>
                <div style="font-size: 13px; color: #737373;">{% if quick_stats.low_stock_items > 0 %}Need restocking{% else %}All good{% endif %}</div>
            </div>
        </div>
        {% endif %}
        
        {% if not has_shopify %}
        <div class="banner banner-info" style="background: #ffffff; border: 1px solid #e1e3e5; border-left: 3px solid #008060;">
            <div class="banner-content" style="flex: 1;">
                <h3 style="margin-bottom: 8px; font-size: 16px; font-weight: 600; color: #202223;">Connect your Shopify store</h3>
                <p style="margin-bottom: 0; font-size: 14px; color: #6d7175;">Get started in 30 seconds. Connect your store to unlock order monitoring, inventory management, and revenue analytics.</p>
            </div>
            <a href="/settings/shopify" class="banner-action">Connect Store →</a>
        </div>
        {% endif %}
        
        <div class="cards-grid">
            <div class="card">
                <div class="card-icon">📦</div>
                <div class="card-title">Order Processing</div>
                <div class="card-description">View pending and unfulfilled Shopify orders. Monitor order status and payment information.</div>
                {% if has_access %}
                <button type="button" class="card-btn" data-action="processOrders" aria-label="View pending orders">
                    <span>View Orders</span>
                    <span style="font-size: 12px; opacity: 0.8;">→</span>
                </button>
                {% else %}
                <button type="button" class="card-btn" onclick="showSubscribePrompt()" style="opacity: 0.6; cursor: not-allowed;" disabled aria-label="Subscribe to view orders">
                    <span>View Orders</span>
                    <span style="font-size: 12px; opacity: 0.8;">→</span>
                </button>
                {% endif %}
            </div>
            
            <div class="card">
                <div class="card-icon">📊</div>
                <div class="card-title">Inventory Management</div>
                <div class="card-description">Monitor stock levels across all products. Get low-stock alerts and complete inventory visibility.</div>
                {% if has_access %}
                <button type="button" class="card-btn" data-action="updateInventory" aria-label="Check inventory levels">
                    <span>Check Inventory</span>
                    <span style="font-size: 12px; opacity: 0.8;">→</span>
                </button>
                {% else %}
                <button type="button" class="card-btn" onclick="showSubscribePrompt()" style="opacity: 0.6; cursor: not-allowed;" disabled aria-label="Subscribe to check inventory">
                    <span>Check Inventory</span>
                    <span style="font-size: 12px; opacity: 0.8;">→</span>
                </button>
                {% endif %}
            </div>
            
            <div class="card">
                <div class="card-icon">💰</div>
                <div class="card-title">Revenue Analytics</div>
                <div class="card-description">Generate revenue reports with product-level breakdown and insights.</div>
                {% if has_access %}
                <button type="button" class="card-btn" data-action="generateReport" aria-label="Generate revenue report">
                    <span>Generate Report</span>
                    <span style="font-size: 12px; opacity: 0.8;">→</span>
                </button>
                {% else %}
                <button type="button" class="card-btn" onclick="showSubscribePrompt()" style="opacity: 0.6; cursor: not-allowed;" disabled aria-label="Subscribe to generate reports">
                    <span>Generate Report</span>
                    <span style="font-size: 12px; opacity: 0.8;">→</span>
                </button>
                {% endif %}
            </div>
        </div>
        
        <div id="connection-status" style="display: none; margin-bottom: 16px;"></div>
        <div class="output-container">
            <div class="output-header">Results</div>
            <div id="output"></div>
        </div>
    </div>
    
    <script>
        // ============================================================================
        // COMPREHENSIVE JAVASCRIPT ERROR LOGGING - Capture EVERY error crumb
        // ============================================================================
        
        // CRITICAL: Store original console.error BEFORE intercepting it
        // This prevents infinite recursion when logJavaScriptError uses console.error
        var originalConsoleError = console.error;
        
        
        // Function to log JavaScript errors to backend
        // Uses originalConsoleError to prevent infinite recursion
        function logJavaScriptError(errorType, errorMessage, errorLocation, errorData, stackTrace) {
            try {
                // #region agent log
                try {
                    fetch('http://127.0.0.1:7242/ingest/98f7b8ce-f573-4ca3-b4d4-0fb2bf283c8d',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'app.py:logJavaScriptError','message':'JavaScript error captured','data':{'error_type':errorType,'error_message':errorMessage.substring(0,200),'error_location':errorLocation,'has_stack':!!stackTrace,'stack_preview':stackTrace ? stackTrace.substring(0,300) : 'none','error_data_keys':Object.keys(errorData || {})},"timestamp":Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(function(){});
                } catch(e) {}
                // #endregion
                
                var errorLog = {
                    timestamp: new Date().toISOString(),
                    error_type: errorType,
                    error_message: errorMessage,
                    error_location: errorLocation,
                    stack_trace: stackTrace,
                    error_data: errorData || {},
                    user_agent: navigator.userAgent,
                    url: window.location.href,
                    referer: document.referrer,
                    viewport: {
                        width: window.innerWidth,
                        height: window.innerHeight
                    },
                    session_id: 'js-session-' + Date.now()
                };
                
                // Send to backend error logging endpoint
                fetch('/api/log_error', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(errorLog),
                    credentials: 'include'
                }).catch(function(err) {
                    // Use originalConsoleError to prevent recursion
                    originalConsoleError('Failed to log error to backend:', err);
                    originalConsoleError('Original error:', errorLog);
                });
                
                // Log to console using originalConsoleError to prevent recursion
                originalConsoleError('[ERROR LOGGED]', errorType, ':', errorMessage);
                originalConsoleError('Location:', errorLocation);
                originalConsoleError('Stack:', stackTrace);
                if (errorData) originalConsoleError('Data:', errorData);
            } catch (e) {
                // Last resort - use originalConsoleError to prevent recursion
                originalConsoleError('Error logging system failed:', e);
                originalConsoleError('Original error:', errorMessage);
            }
        }
        
        // Global error handler - catches ALL unhandled errors
        window.addEventListener('error', function(event) {
            logJavaScriptError(
                'JavaScriptError',
                event.message || 'Unknown error',
                event.filename + ':' + event.lineno + ':' + event.colno,
                {
                    error: event.error ? event.error.toString() : null,
                    type: event.type,
                    target: event.target ? event.target.tagName : null
                },
                event.error ? (event.error.stack || 'No stack trace') : 'No stack trace'
            );
        }, true); // Use capture phase to catch all errors
        
        // Unhandled promise rejection handler - Enhanced to prevent freezing
        window.addEventListener('unhandledrejection', function(event) {
            // #region agent log
            try {
                var error = event.reason;
                var errorMsg = error ? (error.message || error.toString() || 'Unhandled promise rejection') : 'Unknown promise rejection';
                fetch('http://127.0.0.1:7242/ingest/98f7b8ce-f573-4ca3-b4d4-0fb2bf283c8d',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'app.py:unhandledrejection','message':'Unhandled promise rejection','data':{'error_message':errorMsg.substring(0,200),'error_type':error ? error.name : 'none','has_stack':!!(error && error.stack)},"timestamp":Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(function(){});
            } catch(e) {}
            // #endregion
            var error = event.reason;
            var errorMessage = error ? (error.message || error.toString() || 'Unhandled promise rejection') : 'Unknown promise rejection';
            var stackTrace = error && error.stack ? error.stack : 'No stack trace';
            
            // Use originalConsoleError to prevent recursion
            originalConsoleError('❌ Unhandled promise rejection:', error);
            originalConsoleError('This may cause the application to freeze. Error:', errorMessage);
            
            logJavaScriptError(
                'UnhandledPromiseRejection',
                errorMessage,
                'Promise rejection',
                {
                    reason: error ? error.toString() : null,
                    promise: event.promise ? event.promise.toString() : null
                },
                stackTrace
            );
            
            // Prevent default browser error handling and application freeze
            event.preventDefault();
            
            // Show user-friendly error message if possible
            try {
                var outputEl = document.getElementById('output');
                if (outputEl) {
                    outputEl.innerHTML = '<div style="padding: 20px; background: #fff4f4; border: 1px solid #fecaca; border-radius: 8px;"><div style="font-size: 15px; font-weight: 600; color: #d72c0d; margin-bottom: 8px;">⚠️ An error occurred</div><div style="font-size: 14px; color: #6d7175;">Please refresh the page and try again.</div></div>';
                }
            } catch(e) {
                // If showing error fails, use originalConsoleError to prevent recursion
                originalConsoleError('Failed to show error message:', e);
            }
        });
        
        // Console error interceptor (catches console.error calls)
        // CRITICAL: originalConsoleError is already defined above to prevent recursion
        console.error = function() {
            var args = Array.prototype.slice.call(arguments);
            
            // Build error message from arguments
            var errorMessage = args.map(function(arg) {
                if (typeof arg === 'object') {
                    try {
                        return JSON.stringify(arg);
                    } catch(e) {
                        return arg.toString();
                    }
                }
                return String(arg);
            }).join(' ');
            
            // Skip logging if this is from our own error logging system (prevents recursion)
            if (errorMessage.includes('[ERROR LOGGED]') || 
                errorMessage.includes('Failed to log error to backend') ||
                errorMessage.includes('Error logging system failed')) {
                // This is our own logging, just call original and return
                originalConsoleError.apply(console, args);
                return;
            }
            
            // Log the error (logJavaScriptError uses originalConsoleError, so no recursion)
            logJavaScriptError(
                'ConsoleError',
                errorMessage,
                'console.error',
                {arguments: args},
                new Error().stack || 'No stack trace'
            );
            
            // Call original console.error
            originalConsoleError.apply(console, args);
        };
        
        // Try-catch wrapper for async functions
        window.addEventListener('unhandledrejection', function(event) {
            // Already handled above, but ensure we catch everything
        });
        
        // ============================================================================
        // END COMPREHENSIVE JAVASCRIPT ERROR LOGGING
        // ============================================================================
        
        
        // Early function check - verify functions will be available (before definitions)
        console.log('🔍 Early function check (before definitions):', {
            processOrders: typeof window.processOrders,
            updateInventory: typeof window.updateInventory,
            generateReport: typeof window.generateReport
        });
        // Professional request management - prevent duplicate requests and cancel previous ones
        var activeRequests = {
            processOrders: null,
            updateInventory: null,
            generateReport: null
        };
        
        // Debounce timers to prevent rapid clicks
        var debounceTimers = {
            processOrders: null,
            updateInventory: null,
            generateReport: null
        };
        
        // Get APP_URL from template or use current origin (FIXED: was using template literal incorrectly)
        var APP_URL = '{{ APP_URL|default("") }}' || window.location.origin;
        
        // Network status detection with visual indicator
        var isOnline = navigator.onLine;
        function updateConnectionStatus() {
            var statusEl = document.getElementById('connection-status');
            if (statusEl) {
                if (isOnline) {
                    statusEl.style.display = 'none';
                } else {
                    statusEl.style.display = 'block';
                    statusEl.innerHTML = '<div style="padding: 8px 16px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 6px; font-size: 13px; color: #202223; text-align: center;">⚠️ No internet connection</div>';
                }
            }
        }
        
        window.addEventListener('online', function() {
            isOnline = true;
            // Connection restored
            updateConnectionStatus();
            // Show success message
            var statusEl = document.getElementById('connection-status');
            if (statusEl) {
                statusEl.style.display = 'block';
                statusEl.innerHTML = '<div style="padding: 8px 16px; background: #f0fdf4; border: 1px solid #86efac; border-radius: 6px; font-size: 13px; color: #166534; text-align: center;">✅ Connection restored</div>';
                setTimeout(function() {
                    statusEl.style.display = 'none';
                }, 3000);
            }
        });
        window.addEventListener('offline', function() {
            isOnline = false;
            // Connection lost
            updateConnectionStatus();
        });
        
        // Cancel previous request if user clicks another button
        function cancelPreviousRequest(requestType) {
            if (activeRequests[requestType] && activeRequests[requestType].abort) {
                activeRequests[requestType].abort();
                activeRequests[requestType] = null;
            }
        }
        
        // Debounce function to prevent rapid clicks (professional standard)
        function debounce(func, requestType, delay) {
            return function() {
                var context = this;
                var args = arguments;
                
                // Cancel previous timer
                if (debounceTimers[requestType]) {
                    clearTimeout(debounceTimers[requestType]);
                }
                
                // Set new timer
                debounceTimers[requestType] = setTimeout(function() {
                    func.apply(context, args);
                    debounceTimers[requestType] = null;
                }, delay);
            };
        }
        
        function showSubscribePrompt() {
            document.getElementById('output').innerHTML = `
                <div style="padding: 32px; background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); border-radius: 16px; border: 2px solid #dc2626; text-align: center; animation: fadeIn 0.3s ease-in;">
                    <div style="font-size: 48px; margin-bottom: 16px;">🔒</div>
                    <h3 style="color: #dc2626; margin-bottom: 12px; font-size: 20px;">Subscription Required</h3>
                    <p style="color: #991b1b; margin-bottom: 8px; font-size: 15px;">Your trial has ended.</p>
                    <p style="color: #737373; margin-bottom: 24px; font-size: 14px;">Subscribe now to continue using all Employee Suite features.</p>
                    <a href="{% if host %}{{ APP_URL }}/subscribe?shop={{ shop }}&host={{ host }}{% else %}{{ url_for('billing.subscribe') }}{% if shop %}?shop={{ shop }}{% endif %}{% endif %}" style="display: inline-block; background: #0a0a0a; color: #fff; padding: 14px 28px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 15px; transition: all 0.2s;">Subscribe Now →</a>
                    <p style="color: #737373; margin-top: 16px; font-size: 13px;">$29/month • 7-day money-back guarantee</p>
                </div>
            `;
        }
        
        function showLoading(message = 'Processing...') {
            // Professional skeleton loading state (like top Shopify apps)
            document.getElementById('output').innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <div class="loading-text">${message}</div>
                    <div style="margin-top: 16px; font-size: 12px; color: #8c9196;">This may take a few moments...</div>
                </div>
            `;
        }
        
        function showSkeletonLoading() {
            // Skeleton screen for better perceived performance
            var skeleton = '<div style="animation: fadeIn 0.3s ease-in;">';
            for (var i = 0; i < 5; i++) {
                skeleton += '<div style="padding: 16px; margin-bottom: 12px; background: #f6f6f7; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">';
                skeleton += '<div style="flex: 1;"><div style="height: 16px; background: #e1e3e5; border-radius: 4px; width: 60%; margin-bottom: 8px; animation: pulse 1.5s ease-in-out infinite;"></div>';
                skeleton += '<div style="height: 12px; background: #e1e3e5; border-radius: 4px; width: 40%; animation: pulse 1.5s ease-in-out infinite;"></div></div>';
                skeleton += '<div style="height: 20px; width: 60px; background: #e1e3e5; border-radius: 4px; animation: pulse 1.5s ease-in-out infinite;"></div>';
                skeleton += '</div>';
            }
            skeleton += '</div>';
            skeleton += '<style>@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }</style>';
            document.getElementById('output').innerHTML = skeleton;
        }
        
        function setButtonLoading(button, isLoading) {
            if (isLoading) {
                button.disabled = true;
                button.style.opacity = '0.7';
                button.style.cursor = 'wait';
                const originalText = button.innerHTML;
                button.dataset.originalText = originalText;
                button.innerHTML = '<span style="display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.6s linear infinite; margin-right: 8px;"></span>Loading...';
            } else {
                button.disabled = false;
                button.style.opacity = '1';
                button.style.cursor = 'pointer';
                if (button.dataset.originalText) {
                    button.innerHTML = button.dataset.originalText;
                    delete button.dataset.originalText;
                }
            }
        }
        
        function processOrders(button) {
            // Debug logging removed for performance - only log errors if needed
            // Prevent rapid clicks (debounce)
            if (debounceTimers.processOrders) {
                return; // Already processing
            }
            
            // Cancel previous request if exists
            cancelPreviousRequest('processOrders');
            
            // Check network status
            if (!isOnline) {
                document.getElementById('output').innerHTML = `
                    <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                        <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">No Internet Connection</div>
                        <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">Please check your internet connection and try again.</div>
                        <button onclick="processOrders(this)" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                    </div>
                `;
                return;
            }
            
            setButtonLoading(button, true);
            showSkeletonLoading(); // Show skeleton immediately for better UX
            setTimeout(function() {
                showLoading('Loading orders...');
            }, 100);
            
            // Create AbortController for request cancellation
            var controller = new AbortController();
            activeRequests.processOrders = controller;
            
            // Get session token if in embedded mode - seamless integration
            var fetchPromise;
            var isEmbedded = window.isEmbedded; // Use global flag
            
            // PERFECTED: Wait for App Bridge (uses Promise if available, sync check as fallback)
            if (isEmbedded) {
                // Try Promise-based wait first
                if (window.waitForAppBridge && typeof window.waitForAppBridge === 'function' && !window.appBridgeReady) {
                    // Wait for Promise to resolve
                    window.waitForAppBridge().then(function(bridgeState) {
                        if (bridgeState && bridgeState.ready && bridgeState.app) {
                            window.shopifyApp = bridgeState.app;
                            window.appBridgeReady = true;
                            // Continue with API call directly (don't retry function - skip debounce)
                proceedWithApiCall();
                        } else {
                            setButtonLoading(button, false);
                            document.getElementById('output').innerHTML = `
                                <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                                    <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ App Bridge Not Ready</div>
                                    <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">${bridgeState && bridgeState.error ? bridgeState.error : 'Please wait while the app initializes.'}</div>
                                    <button onclick="var btn = document.querySelector('.card-btn[onclick*=\"processOrders\"]'); if (btn) setTimeout(function(){processOrders(btn);}, 500);" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                                </div>
                            `;
                        }
                    }).catch(function(error) {
                        setButtonLoading(button, false);
                        document.getElementById('output').innerHTML = `
                            <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fff4f4; border: 1px solid #fecaca; border-radius: 8px;">
                                <div style="font-size: 15px; font-weight: 600; color: #d72c0d; margin-bottom: 8px;">❌ App Bridge Error</div>
                                <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">${error.message || 'Please refresh the page.'}</div>
                                <button onclick="window.location.reload()" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Refresh Page</button>
                            </div>
                        `;
                    });
                    return;
                } else if (!window.appBridgeReady) {
                    // Fallback to original sync check
                setButtonLoading(button, false);
                document.getElementById('output').innerHTML = `
                    <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                        <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ Initializing App...</div>
                        <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">Please wait while the app initializes. This should only take a moment.</div>
                        <button onclick="var btn = document.querySelector('.card-btn[onclick*=\"processOrders\"]'); if (btn) setTimeout(function(){processOrders(btn);}, 500);" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                    </div>
                `;
                } // Close else if (!window.appBridgeReady)
            } // Close if (isEmbedded)
            
            // Extract API call logic into function (called when Promise resolves or App Bridge ready)
            function proceedWithApiCall() {
                // Debug logging removed for performance
                if (isEmbedded && window.shopifyApp && window.appBridgeReady) {
                // In embedded mode, we MUST have session token - retry up to 3 times
                var retryCount = 0;
                var maxRetries = 2; // Optimized: reduced from 3
                
                function getTokenWithRetry() {
                    // Debug logging removed for performance
                    return window.shopifyApp.getSessionToken().then(function(token) {
                        if (!token && retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve, reject) {
                                setTimeout(function() { getTokenWithRetry().then(resolve).catch(reject); }, 100); // Optimized: reduced from 300ms
                            });
                        }
                        return token;
                    }).catch(function(err) {
                        // Debug logging removed for performance - only log if max retries exceeded
                        // If error and haven't exceeded retries, retry
                        if (retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve, reject) {
                                setTimeout(function() { getTokenWithRetry().then(resolve).catch(reject); }, 100); // Optimized: reduced from 300ms
                            });
                        }
                        // Max retries exceeded, throw error
                        throw err;
                    });
                }
                
                fetchPromise = getTokenWithRetry().then(function(token) {
                    if (!token) {
                        throw new Error('Unable to get session token. Please refresh the page.');
                    }
                    // CRITICAL: Use absolute URL in embedded mode to prevent iframe URL resolution issues
                    var apiUrl = '/api/process_orders';
                    if (isEmbedded) {
                        apiUrl = APP_URL + '/api/process_orders';
                    }
                    // Debug logging removed for performance
                    return fetch(apiUrl, {
                        headers: {'Authorization': 'Bearer ' + token},
                        signal: controller.signal
                    });
                }).catch(function(err) {
                    // Debug logging removed for performance
                    // Don't show error if request was cancelled
                    if (err.name === 'AbortError') {
                        return;
                    }
                    // Show detailed error for debugging
                    console.error('❌ Session token error:', err);
                    setButtonLoading(button, false);
                    var errorMsg = err.message || 'Unknown error';
                    document.getElementById('output').innerHTML = `
                        <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fff4f4; border: 1px solid #fecaca; border-radius: 8px;">
                            <div style="font-size: 15px; font-weight: 600; color: #d72c0d; margin-bottom: 8px;">🔒 Session Token Error</div>
                            <div style="font-size: 14px; color: #6d7175; margin-bottom: 12px; line-height: 1.5;">${errorMsg}</div>
                            <div style="font-size: 13px; color: #8c9196; margin-bottom: 16px; padding: 12px; background: #f6f6f7; border-radius: 4px;">
                                <strong>Debug info:</strong><br>
                                App Bridge ready: ${window.appBridgeReady ? 'Yes' : 'No'}<br>
                                App Bridge exists: ${window.shopifyApp ? 'Yes' : 'No'}<br>
                                Embedded mode: ${window.isEmbedded ? 'Yes' : 'No'}
                            </div>
                            <button onclick="window.location.reload()" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; margin-right: 8px;">Refresh Page</button>
                            <button onclick="console.log('App Bridge:', window.shopifyApp, 'Ready:', window.appBridgeReady)" style="padding: 8px 16px; background: #f6f6f7; color: #202223; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Debug Console</button>
                        </div>
                    `;
                    throw err; // Stop execution
                });
            } else {
                // Debug logging removed for performance
                // Not embedded - use regular fetch (Flask-Login handles auth)
                // CRITICAL: Include credentials (cookies) for standalone access
                fetchPromise = fetch('/api/process_orders', {
                    signal: controller.signal,
                    credentials: 'include'
                });
            }

            // Execute the Promise chain
            fetchPromise
                .then(r => {
                    // Debug logging removed for performance
                    // Check if request was cancelled
                    if (controller.signal.aborted) {
                        return null;
                    }
                    // Enhanced API response verification per external feedback
                    console.log('📡 API Response received:', {
                        status: r.status,
                        statusText: r.statusText,
                        url: r.url,
                        ok: r.ok,
                        contentType: r.headers.get('content-type')
                    });
                    
                    if (!r.ok) {
                        // Enhanced error logging per external feedback
                        console.error('❌ API request failed:', {
                            status: r.status,
                            statusText: r.statusText,
                            url: r.url,
                            ok: r.ok
                        });
                        if (r.status === 404) {
                            console.error('❌ 404 Not Found - Endpoint does not exist:', r.url);
                            console.error('This may indicate a missing API route or incorrect URL');
                        } else if (r.status === 500) {
                            console.error('❌ 500 Internal Server Error - Server-side error occurred');
                            console.error('Check server logs for detailed error information');
                        }
                        // Try to parse JSON, but handle non-JSON responses
                        return r.text().then(function(text) {
                            var err = {};
                            try {
                                err = JSON.parse(text);
                            } catch(e) {
                                // Not JSON - use text as error message
                                err = {error: text || 'Unknown error', message: text || 'Unknown error'};
                            }
                            // Extract error from multiple possible fields
                            var errorMsg = err.error || err.message || err.detail || err.description || (typeof err === 'string' ? err : 'API error unknown');
                            throw new Error(errorMsg);
                        });
                    }
                    return r.json();
                })
                .then(d => {
                    // Check if request was cancelled
                    if (!d) return;
                    
                    setButtonLoading(button, false);
                    activeRequests.processOrders = null;
                    if (debounceTimers.processOrders) {
                        clearTimeout(debounceTimers.processOrders);
                        debounceTimers.processOrders = null;
                    }
                    
                    if (d.success) {
                        const icon = '✅';
                        document.getElementById('output').innerHTML = `
                            <div style="animation: fadeIn 0.3s ease-in;">
                                <h3 class="success" style="display: flex; align-items: center; gap: 8px;">
                                    <span>${icon}</span>
                                    <span>Orders Loaded</span>
                                </h3>
                                <div style="margin-top: 12px; line-height: 1.6;">${d.message || d.error || 'No details available'}</div>
                            </div>
                        `;
                    } else {
                        // Professional error display with actionable buttons
                        var errorHtml = '<div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">';
                        errorHtml += '<div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">' + (d.error || 'Something went wrong') + '</div>';
                        if (d.message) {
                            errorHtml += '<div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">' + d.message + '</div>';
                        }
                        if (d.action === 'refresh') {
                            errorHtml += '<button onclick="window.location.reload()" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Refresh Page</button>';
                        } else if (d.action === 'subscribe' && d.subscribe_url) {
                            errorHtml += '<a href="' + d.subscribe_url + '" style="display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; font-size: 14px; font-weight: 500; text-decoration: none;">Subscribe Now</a>';
                        } else if (d.action === 'install') {
                            errorHtml += '<a href="/settings/shopify" style="display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; font-size: 14px; font-weight: 500; text-decoration: none;">Connect Store</a>';
                        } else if (d.action === 'retry') {
                            errorHtml += '<button onclick="processOrders(this)" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>';
                        }
                        errorHtml += '</div>';
                        document.getElementById('output').innerHTML = errorHtml;
                    }
                })
                .catch(err => {
                    // Enhanced error handling per external feedback - prevent application freezing
                    console.error('❌ Failed to process orders:', err);
                    console.error('Error details:', {
                        message: err.message,
                        name: err.name,
                        stack: err.stack ? err.stack.substring(0, 300) : 'no stack'
                    });
                    
                    
                    // Always re-enable button and clear timers to prevent freezing
                    setButtonLoading(button, false);
                    activeRequests.processOrders = null;
                    if (debounceTimers.processOrders) {
                        clearTimeout(debounceTimers.processOrders);
                        debounceTimers.processOrders = null;
                    }
                    console.error('❌ API request error:', err);
                    var errorDetails = '';
                    if (err.message) {
                        errorDetails = '<div style="font-size: 12px; color: #8c9196; margin-top: 8px; padding: 8px; background: #f6f6f7; border-radius: 4px;">' + err.message + '</div>';
                    }
                    document.getElementById('output').innerHTML = `
                        <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fff4f4; border: 1px solid #fecaca; border-radius: 8px;">
                            <h3 class="error" style="color: #d72c0d; margin-bottom: 12px;">❌ Connection Error</h3>
                            <p style="margin-top: 12px; color: #6d7175;">Unable to connect to server. Please check your internet connection and try again.</p>
                            ${errorDetails}
                            <p style="margin-top: 12px; font-size: 13px; color: #737373;">💡 Tip: If this persists, go to Settings and verify your Shopify store is connected.</p>
                            <button onclick="processOrders(this)" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; margin-top: 12px;">Try Again</button>
                        </div>
                    `;
                });
            } // Close proceedWithApiCall function
            
            // Call proceedWithApiCall to execute the promise chain
            proceedWithApiCall();
            } // Close processOrders function
        
        // Ensure function is in global scope
        window.processOrders = processOrders;
        
        function updateInventory(button) {
            // Debug logging removed for performance - only log errors if needed
            // Prevent rapid clicks (debounce)
            if (debounceTimers.updateInventory) {
                return; // Already processing
            }
            
            // Cancel previous request if exists
            cancelPreviousRequest('updateInventory');
            
            // Check network status
            if (!isOnline) {
                document.getElementById('output').innerHTML = `
                    <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                        <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">No Internet Connection</div>
                        <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">Please check your internet connection and try again.</div>
                        <button onclick="updateInventory(this)" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                    </div>
                `;
                return;
            }
            
            setButtonLoading(button, true);
            showSkeletonLoading(); // Show skeleton immediately for better UX
            setTimeout(function() {
                showLoading('Loading inventory...');
            }, 100);
            
            // Create AbortController for request cancellation
            var controller = new AbortController();
            activeRequests.updateInventory = controller;
            
            // Get session token if in embedded mode - seamless integration
            var fetchPromise;
            var isEmbedded = window.isEmbedded; // Use global flag
            
            // PERFECTED: Wait for App Bridge (uses Promise if available, sync check as fallback)
            if (isEmbedded) {
                // Try Promise-based wait first
                if (window.waitForAppBridge && typeof window.waitForAppBridge === 'function' && !window.appBridgeReady) {
                    // Wait for Promise to resolve
                    window.waitForAppBridge().then(function(bridgeState) {
                        if (bridgeState && bridgeState.ready && bridgeState.app) {
                            window.shopifyApp = bridgeState.app;
                            window.appBridgeReady = true;
                            // Continue with API call directly (don't retry function - skip debounce)
                            proceedWithApiCall();
                        } else {
                            setButtonLoading(button, false);
                            document.getElementById('output').innerHTML = `
                                <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                                    <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ App Bridge Not Ready</div>
                                    <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">${bridgeState && bridgeState.error ? bridgeState.error : 'Please wait while the app initializes.'}</div>
                                    <button onclick="var btn = document.querySelector('.card-btn[onclick*=\"processOrders\"]'); if (btn) setTimeout(function(){processOrders(btn);}, 500);" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                                </div>
                            `;
                        }
                    }).catch(function(error) {
                        setButtonLoading(button, false);
                        document.getElementById('output').innerHTML = `
                            <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fff4f4; border: 1px solid #fecaca; border-radius: 8px;">
                                <div style="font-size: 15px; font-weight: 600; color: #d72c0d; margin-bottom: 8px;">❌ App Bridge Error</div>
                                <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">${error.message || 'Please refresh the page.'}</div>
                                <button onclick="window.location.reload()" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Refresh Page</button>
                            </div>
                        `;
                    });
                    return;
                } else if (!window.appBridgeReady) {
                    // Fallback to original sync check
                setButtonLoading(button, false);
                document.getElementById('output').innerHTML = `
                    <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                        <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ Initializing App...</div>
                        <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">Please wait while the app initializes. This should only take a moment.</div>
                        <button onclick="var btn = document.querySelector('.card-btn[onclick*=\"updateInventory\"]'); if (btn) setTimeout(function(){updateInventory(btn);}, 500);" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                    </div>
                `;
                } // Close else if (!window.appBridgeReady)
            } // Close if (isEmbedded)
            
            // Extract API call logic into function (called when Promise resolves or App Bridge ready)
            function proceedWithApiCall() {
                if (isEmbedded && window.shopifyApp && window.appBridgeReady) {
                // In embedded mode, we MUST have session token - retry up to 3 times
                var retryCount = 0;
                var maxRetries = 2; // Optimized: reduced from 3
                
                function getTokenWithRetry() {
                    return window.shopifyApp.getSessionToken().then(function(token) {
                        if (!token && retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve, reject) {
                                setTimeout(function() { getTokenWithRetry().then(resolve).catch(reject); }, 100); // Optimized: reduced from 300ms
                            });
                        }
                        return token;
                }).catch(function(err) {
                        // If error and haven't exceeded retries, retry
                        if (retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve, reject) {
                                setTimeout(function() { getTokenWithRetry().then(resolve).catch(reject); }, 100); // Optimized: reduced from 300ms
                            });
                        }
                        // Max retries exceeded, throw error
                        throw err;
                    });
                }
                
                fetchPromise = getTokenWithRetry().then(function(token) {
                    if (!token) {
                        throw new Error('Unable to get session token. Please refresh the page.');
                    }
                    // CRITICAL: Use absolute URL in embedded mode to prevent iframe URL resolution issues
                    var apiUrl = '/api/update_inventory';
                    if (isEmbedded) {
                        apiUrl = APP_URL + '/api/update_inventory';
                    }
                    // Debug logging removed for performance
                    return fetch(apiUrl, {
                        headers: {'Authorization': 'Bearer ' + token},
                        signal: controller.signal
                    });
                }).catch(function(err) {
                    // Don't show error if request was cancelled
                    if (err.name === 'AbortError') {
                        return;
                    }
                    // Show professional error instead of trying without auth
                    setButtonLoading(button, false);
                    document.getElementById('output').innerHTML = `
                        <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                            <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">Session Error</div>
                            <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">Unable to verify your session. This usually happens when the page has been open for a while.</div>
                            <button onclick="window.location.reload()" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Refresh Page</button>
                        </div>
                    `;
                    throw err; // Stop execution
                });
            } else {
                // Not embedded - use regular fetch (Flask-Login handles auth)
                // CRITICAL: Include credentials (cookies) for standalone access
                fetchPromise = fetch('/api/update_inventory', {
                    signal: controller.signal,
                    credentials: 'include'  // Include cookies for Flask-Login
                });
            }
            
            // Execute the Promise chain
            fetchPromise
                .then(r => {
                    // Check if request was cancelled
                    if (controller.signal.aborted) {
                        return null;
                    }
                    if (!r.ok) {
                        return r.text().then(text => {
                            try {
                                var json = JSON.parse(text);
                                var errorMsg = json.error || json.message || json.detail || json.description || 'Request failed';
                                throw new Error(errorMsg);
                            } catch (e) {
                                if (e.message && e.message !== 'Request failed') throw e;
                                throw new Error(text || 'Network error');
                            }
                        });
                    }
                    return r.json();
                })
                .then(d => {
                    // Check if request was cancelled
                    if (!d) return;
                    
                    setButtonLoading(button, false);
                    activeRequests.updateInventory = null;
                    if (debounceTimers.updateInventory) {
                        clearTimeout(debounceTimers.updateInventory);
                        debounceTimers.updateInventory = null;
                    }
                    
                    if (d.success) {
                        const icon = '✅';
                        document.getElementById('output').innerHTML = `
                            <div style="animation: fadeIn 0.3s ease-in;">
                                <h3 class="success" style="display: flex; align-items: center; gap: 8px;">
                                    <span>${icon}</span>
                                    <span>Inventory Updated</span>
                                </h3>
                                <div style="margin-top: 12px; white-space: pre-wrap; line-height: 1.6;">${d.message || d.error || 'No details available'}</div>
                            </div>
                        `;
                    } else {
                        // Professional error display with actionable buttons
                        var errorHtml = '<div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">';
                        errorHtml += '<div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">' + (d.error || 'Something went wrong') + '</div>';
                        if (d.message) {
                            errorHtml += '<div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">' + d.message + '</div>';
                        }
                        if (d.action === 'refresh') {
                            errorHtml += '<button onclick="window.location.reload()" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Refresh Page</button>';
                        } else if (d.action === 'subscribe' && d.subscribe_url) {
                            errorHtml += '<a href="' + d.subscribe_url + '" style="display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; font-size: 14px; font-weight: 500; text-decoration: none;">Subscribe Now</a>';
                        } else if (d.action === 'install') {
                            errorHtml += '<a href="/settings/shopify" style="display: inline-block; padding: 8px 16px; background: #008060; color: #fff; border-radius: 6px; font-size: 14px; font-weight: 500; text-decoration: none;">Connect Store</a>';
                        } else if (d.action === 'retry') {
                            errorHtml += '<button onclick="updateInventory(this)" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>';
                        } else {
                            // Fallback: try to display HTML error if it's HTML
                            if (d.error && d.error.includes('<')) {
                                errorHtml = '<div style="animation: fadeIn 0.3s ease-in;">' + d.error + '</div>';
                            }
                        }
                        if (!errorHtml.includes('</div>')) errorHtml += '</div>';
                        document.getElementById('output').innerHTML = errorHtml;
                    }
                })
                .catch(err => {
                    // Don't show error if request was cancelled
                    if (err.name === 'AbortError') {
                        return;
                    }
                    
                    setButtonLoading(button, false);
                    activeRequests.updateInventory = null;
                    if (debounceTimers.updateInventory) {
                        clearTimeout(debounceTimers.updateInventory);
                        debounceTimers.updateInventory = null;
                    }
                    
                    var errorMessage = 'Unable to connect to server. Please check your internet connection and try again.';
                    if (!isOnline) {
                        errorMessage = 'No internet connection. Please check your network and try again.';
                    }
                    
                    document.getElementById('output').innerHTML = `
                        <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                            <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">Connection Error</div>
                            <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">${errorMessage}</div>
                            <button onclick="updateInventory(this)" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; margin-right: 8px;">Try Again</button>
                            <a href="/settings/shopify" style="display: inline-block; padding: 8px 16px; background: #f6f6f7; color: #202223; border-radius: 6px; font-size: 14px; font-weight: 500; text-decoration: none;">Check Settings</a>
                        </div>
                    `;
                });
            } // Close proceedWithApiCall function
            
            // Call proceedWithApiCall to execute the promise chain
            proceedWithApiCall();
        }
        
        // Ensure function is in global scope
        window.updateInventory = updateInventory;
        
        function generateReport(button) {
            // Debug logging removed for performance - only log errors if needed
            // Prevent rapid clicks (debounce)
            if (debounceTimers.generateReport) {
                return; // Already processing
            }
            
            // Cancel previous request if exists
            cancelPreviousRequest('generateReport');
            
            // Check network status
            if (!isOnline) {
                document.getElementById('output').innerHTML = `
                    <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                        <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">No Internet Connection</div>
                        <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">Please check your internet connection and try again.</div>
                        <button onclick="generateReport(this)" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                    </div>
                `;
                return;
            }
            
            setButtonLoading(button, true);
            showSkeletonLoading(); // Show skeleton immediately for better UX
            setTimeout(function() {
                showLoading('Generating report...');
            }, 100);
            
            // Create AbortController for request cancellation
            var controller = new AbortController();
            activeRequests.generateReport = controller;
            
            // Get session token if in embedded mode - seamless integration
            var fetchPromise;
            var isEmbedded = window.isEmbedded; // Use global flag
            
            // PERFECTED: Wait for App Bridge (uses Promise if available, sync check as fallback)
            if (isEmbedded) {
                // Try Promise-based wait first
                if (window.waitForAppBridge && typeof window.waitForAppBridge === 'function' && !window.appBridgeReady) {
                    // Wait for Promise to resolve
                    window.waitForAppBridge().then(function(bridgeState) {
                        if (bridgeState && bridgeState.ready && bridgeState.app) {
                            window.shopifyApp = bridgeState.app;
                            window.appBridgeReady = true;
                            // Continue with API call directly (don't retry function - skip debounce)
                            proceedWithApiCall();
                        } else {
                            setButtonLoading(button, false);
                            document.getElementById('output').innerHTML = `
                                <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                                    <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ App Bridge Not Ready</div>
                                    <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">${bridgeState && bridgeState.error ? bridgeState.error : 'Please wait while the app initializes.'}</div>
                                    <button onclick="var btn = document.querySelector('.card-btn[onclick*=\"processOrders\"]'); if (btn) setTimeout(function(){processOrders(btn);}, 500);" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                                </div>
                            `;
                        }
                    }).catch(function(error) {
                        setButtonLoading(button, false);
                        document.getElementById('output').innerHTML = `
                            <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fff4f4; border: 1px solid #fecaca; border-radius: 8px;">
                                <div style="font-size: 15px; font-weight: 600; color: #d72c0d; margin-bottom: 8px;">❌ App Bridge Error</div>
                                <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">${error.message || 'Please refresh the page.'}</div>
                                <button onclick="window.location.reload()" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Refresh Page</button>
                            </div>
                        `;
                    });
                    return;
                } else if (!window.appBridgeReady) {
                    // Fallback to original sync check
                setButtonLoading(button, false);
                document.getElementById('output').innerHTML = `
                    <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                        <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ Initializing App...</div>
                        <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">Please wait while the app initializes. This should only take a moment.</div>
                        <button onclick="var btn = document.querySelector('.card-btn[onclick*=\"generateReport\"]'); if (btn) setTimeout(function(){generateReport(btn);}, 500);" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                    </div>
                `;
                } // Close else if (!window.appBridgeReady)
            } // Close if (isEmbedded)
            
            // Extract API call logic into function (called when Promise resolves or App Bridge ready)
            function proceedWithApiCall() {
                if (isEmbedded && window.shopifyApp && window.appBridgeReady) {
                // In embedded mode, we MUST have session token - retry up to 3 times
                var retryCount = 0;
                var maxRetries = 2; // Optimized: reduced from 3
                
                function getTokenWithRetry() {
                    return window.shopifyApp.getSessionToken().then(function(token) {
                        if (!token && retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve, reject) {
                                setTimeout(function() { getTokenWithRetry().then(resolve).catch(reject); }, 100); // Optimized: reduced from 300ms
                            });
                        }
                        return token;
                }).catch(function(err) {
                        // If error and haven't exceeded retries, retry
                        if (retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve, reject) {
                                setTimeout(function() { getTokenWithRetry().then(resolve).catch(reject); }, 100); // Optimized: reduced from 300ms
                            });
                        }
                        // Max retries exceeded, throw error
                        throw err;
                    });
                }
                
                fetchPromise = getTokenWithRetry().then(function(token) {
                    if (!token) {
                        throw new Error('Unable to get session token. Please refresh the page.');
                    }
                    // Get shop from URL or use current shop
                    const shopUrl = new URLSearchParams(window.location.search).get('shop') || '';
                    var reportUrl = shopUrl ? `/api/generate_report?shop=${encodeURIComponent(shopUrl)}` : '/api/generate_report';
                    // CRITICAL: Use absolute URL in embedded mode to prevent iframe URL resolution issues
                    if (isEmbedded) {
                        reportUrl = APP_URL + reportUrl;
                    }
                    // Debug logging removed for performance
                    return fetch(reportUrl, {
                        headers: {'Authorization': 'Bearer ' + token},
                        signal: controller.signal
                    });
                }).catch(function(err) {
                    // Don't show error if request was cancelled
                    if (err.name === 'AbortError') {
                        return;
                    }
                    // Show professional error instead of trying without auth
                    setButtonLoading(button, false);
                    document.getElementById('output').innerHTML = `
                        <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                            <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">Session Error</div>
                            <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">Unable to verify your session. This usually happens when the page has been open for a while.</div>
                            <button onclick="window.location.reload()" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Refresh Page</button>
                        </div>
                    `;
                    throw err; // Stop execution
                });
            } else {
                // Not embedded - use regular fetch (Flask-Login handles auth)
                // CRITICAL: Include credentials (cookies) for standalone access
                // Get shop from URL or use current shop
                const shopUrl = new URLSearchParams(window.location.search).get('shop') || '';
                const reportUrl = shopUrl ? `/api/generate_report?shop=${encodeURIComponent(shopUrl)}` : '/api/generate_report';
                fetchPromise = fetch(reportUrl, {
                    signal: controller.signal,
                    credentials: 'include'  // Include cookies for Flask-Login
                });
            }
            
            // Execute the Promise chain
            fetchPromise
                .then(r => {
                    // Check if request was cancelled
                    if (controller.signal.aborted) {
                        return null;
                    }
                    if (!r.ok) {
                        // If error response, try to get error HTML
                        return r.text().then(html => {
                            throw new Error(html);
                        });
                    }
                    return r.text();
                })
                .then(html => {
                    // Check if request was cancelled
                    if (!html) return;
                    
                    setButtonLoading(button, false);
                    activeRequests.generateReport = null;
                    if (debounceTimers.generateReport) {
                        clearTimeout(debounceTimers.generateReport);
                        debounceTimers.generateReport = null;
                    }
                    
                    // Check if the HTML contains an error message (from backend)
                    if (html.includes('Error Loading revenue') || html.includes('No Shopify store connected')) {
                        // Backend already formatted the error, display directly
                        document.getElementById('output').innerHTML = `<div style="animation: fadeIn 0.3s ease-in;">${html}</div>`;
                    } else {
                        // Success - display with title
                        document.getElementById('output').innerHTML = `
                            <div style="animation: fadeIn 0.3s ease-in;">
                                <h3 class="success" style="display: flex; align-items: center; gap: 8px;">
                                    <span>✅</span>
                                    <span>Revenue Report Generated</span>
                                </h3>
                                <div style="margin-top: 12px; line-height: 1.6;">${html}</div>
                            </div>
                        `;
                    }
                })
                .catch(err => {
                    // Don't show error if request was cancelled
                    if (err.name === 'AbortError') {
                        return;
                    }
                    
                    setButtonLoading(button, false);
                    activeRequests.generateReport = null;
                    if (debounceTimers.generateReport) {
                        clearTimeout(debounceTimers.generateReport);
                        debounceTimers.generateReport = null;
                    }
                    
                    // Check if error message is HTML (from backend) or plain text (network error)
                    if (err.message && err.message.includes('Error Loading revenue')) {
                        // Backend error HTML
                        document.getElementById('output').innerHTML = `<div style="animation: fadeIn 0.3s ease-in;">${err.message}</div>`;
                    } else {
                        // Network error
                        var errorMessage = 'Unable to generate report. Please check your internet connection and try again.';
                        if (!isOnline) {
                            errorMessage = 'No internet connection. Please check your network and try again.';
                        }
                        
                        document.getElementById('output').innerHTML = `
                            <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                                <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">Connection Error</div>
                                <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">${errorMessage}</div>
                                <button onclick="generateReport(this)" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; margin-right: 8px;">Try Again</button>
                                <a href="/settings/shopify" style="display: inline-block; padding: 8px 16px; background: #f6f6f7; color: #202223; border-radius: 6px; font-size: 14px; font-weight: 500; text-decoration: none;">Check Settings</a>
                            </div>
                        `;
                    }
                });
            } // Close proceedWithApiCall function
            
            // Call proceedWithApiCall to execute the promise chain
            proceedWithApiCall();
        }
        
        // Ensure function is in global scope
        window.generateReport = generateReport;
        
        // ============================================================================
        // FUNCTION AVAILABILITY VERIFICATION (Per External Feedback)
        // ============================================================================
        // Log function availability immediately after all assignments
        console.log('Function check:', {
            processOrders: typeof window.processOrders,
            updateInventory: typeof window.updateInventory,
            generateReport: typeof window.generateReport
        });
        
        // Immediate function check after all assignments
        console.log('✅ Function check (after all assignments):', {
            processOrders: typeof window.processOrders,
            updateInventory: typeof window.updateInventory,
            generateReport: typeof window.generateReport
        });
        
        // Verify all functions are properly assigned
        if (typeof window.processOrders !== 'function' ||
            typeof window.updateInventory !== 'function' ||
            typeof window.generateReport !== 'function') {
            console.error('❌ CRITICAL: Functions not properly assigned to window!');
            console.error('Missing functions:', {
                processOrders: typeof window.processOrders !== 'function',
                updateInventory: typeof window.updateInventory !== 'function',
                generateReport: typeof window.generateReport !== 'function'
            });
        } else {
            console.log('✅ All functions successfully assigned to window object');
        }
        
        
        
        // ============================================================================
        // NETWORK REQUEST LOGGING - Capture all API requests (OPTIMIZED)
        // ============================================================================
        // Intercept fetch requests to log network activity
        // CRITICAL: Skip debug endpoint to prevent infinite loops and performance issues
        (function() {
            var originalFetch = window.fetch;
            window.fetch = function(...args) {
                var url = args[0];
                var options = args[1] || {};
                var method = options.method || 'GET';
                
                // CRITICAL: Skip logging for debug endpoint to prevent performance issues
                if (typeof url === 'string' && url.includes('127.0.0.1:7242')) {
                    return originalFetch.apply(this, args);
                }
                
                var startTime = Date.now();
                
                // Only log API requests, not all requests (reduces noise)
                if (typeof url === 'string' && (url.includes('/api/') || url.startsWith('http'))) {
                    console.log('🌐 Network Request:', {
                        url: url,
                        method: method,
                        timestamp: new Date().toISOString()
                    });
                }
                
                // Call original fetch
                return originalFetch.apply(this, args)
                    .then(function(response) {
                        var endTime = Date.now();
                        var duration = endTime - startTime;
                        
                        // Only log API responses, and only if there's an error or slow response
                        if (typeof url === 'string' && (url.includes('/api/') || url.startsWith('http'))) {
                            if (!response.ok || duration > 1000) {
                                console.log('🌐 Network Response:', {
                                    url: url,
                                    method: method,
                                    status: response.status,
                                    statusText: response.statusText,
                                    ok: response.ok,
                                    duration: duration + 'ms',
                                    timestamp: new Date().toISOString()
                                });
                            }
                        }
                        
                        return response;
                    })
                    .catch(function(error) {
                        var endTime = Date.now();
                        var duration = endTime - startTime;
                        
                        // Skip logging GA errors - they're expected to fail in iframes
                        if (typeof url === 'string' && 
                            (url.includes('google-analytics.com') || url.includes('googletagmanager.com'))) {
                            // GA blocked in iframe - silently ignore
                            throw error;
                        }
                        
                        // Only log errors for API requests
                        if (typeof url === 'string' && (url.includes('/api/') || url.startsWith('http'))) {
                            console.error('🌐 Network Error:', {
                                url: url,
                                method: method,
                                error: error.message || 'Unknown error',
                                errorName: error.name || 'Unknown',
                                duration: duration + 'ms',
                                timestamp: new Date().toISOString()
                            });
                        }
                        
                        throw error;
                    });
            };
        })();
        
        // ============================================================================
        // ROBUST BUTTON EVENT HANDLING - Event Delegation Pattern (Most Reliable)
        // ============================================================================
        // Use event delegation - attach ONE listener to document that handles ALL button clicks
        // This works even if buttons are added dynamically or listeners fail to attach
        // FIXED: Always wait for DOMContentLoaded to ensure DOM and dependencies are ready
        // FIXED: Verify functions exist before setting up listener (per external feedback)
        document.addEventListener('DOMContentLoaded', function setupEventDelegation() {
            console.log('✅ DOMContentLoaded fired');
            
            // Verify functions are assigned to window before setting up listener
            var functionsReady = typeof window.processOrders === 'function' &&
                                 typeof window.updateInventory === 'function' &&
                                 typeof window.generateReport === 'function';
            
            if (!functionsReady) {
                console.error('❌ Functions not ready yet. Retrying in 100ms...');
                console.log('Function status:', {
                    processOrders: typeof window.processOrders,
                    updateInventory: typeof window.updateInventory,
                    generateReport: typeof window.generateReport
                });
                // Retry after short delay
                setTimeout(setupEventDelegation, 100);
                return;
            }
            
            console.log('✅ All functions ready:', {
                processOrders: typeof window.processOrders,
                updateInventory: typeof window.updateInventory,
                generateReport: typeof window.generateReport
            });
            
            var buttonsFound = document.querySelectorAll('.card-btn[data-action]').length;
            console.log('✅ Buttons found:', buttonsFound);
            
            
            // CRITICAL: Add EARLY click listener to catch ALL clicks before anything else
            // OPTIMIZED: Only log button clicks to reduce performance impact
            document.addEventListener('click', function(e) {
                // Only log if it's actually a button click (reduces noise)
                var closestBtn = e.target.closest('.card-btn[data-action]');
                if (!closestBtn) return; // Skip non-button clicks
                
            }, true); // Capture phase - fires FIRST
            
            // Attach click listener to document for event delegation (per external feedback)
            document.addEventListener('click', function(e) {
                // Find the closest button with data-action attribute
                var btn = e.target.closest('.card-btn[data-action]');
                if (!btn) {
                    return; // Exit if clicked element is not a button (no logging to reduce noise)
                }
                
                // ENHANCED LOGGING: Capture state before action (OPTIMIZED - minimal logging)
                var action = btn.getAttribute('data-action');
                console.log('✅ Button clicked:', action);
                
                // Check CSS/pointer-events issues (only log if there's a problem)
                var computedStyle = window.getComputedStyle(btn);
                var pointerEvents = computedStyle.pointerEvents;
                var display = computedStyle.display;
                var visibility = computedStyle.visibility;
                
                if (pointerEvents === 'none' || display === 'none' || visibility === 'hidden') {
                    console.warn('⚠️ Button CSS issue:', {
                        pointerEvents: pointerEvents,
                        display: display,
                        visibility: visibility
                    });
                }
                
                
                e.preventDefault(); // Prevent any default behavior
                e.stopPropagation();
                
                if (!action) {
                    console.warn('⚠️ Button has no data-action attribute');
                    return; // No action specified
                }
                
                // Check if button is disabled
                if (btn.disabled) {
                    console.warn('⚠️ Button is disabled, ignoring click');
                    return;
                }
                
                // Route to appropriate function based on data-action (per external feedback)
                // Enhanced error handling to prevent application freezing
                if (window[action] && typeof window[action] === 'function') {
                    try {
                        console.log('✅ Calling function:', action);
                        window[action](btn); // Call the corresponding function
                    } catch(err) {
                        // Catch synchronous errors to prevent freezing
                        console.error('❌ Error executing function:', action, err);
                        console.error('Error details:', {
                            message: err.message,
                            name: err.name,
                            stack: err.stack ? err.stack.substring(0, 300) : 'no stack',
                            buttonState: {
                                disabled: btn.disabled,
                                innerHTML: btn.innerHTML.substring(0, 50)
                            }
                        });
                        // Show user-friendly error message
                        var outputEl = document.getElementById('output');
                        if (outputEl) {
                            outputEl.innerHTML = '<div style="padding: 20px; background: #fff4f4; border: 1px solid #fecaca; border-radius: 8px;"><div style="font-size: 15px; font-weight: 600; color: #d72c0d; margin-bottom: 8px;">❌ Error</div><div style="font-size: 14px; color: #6d7175;">An error occurred: ' + (err.message || 'Unknown error') + '</div></div>';
                        }
                        // Re-enable button
                        btn.disabled = false;
                        if (btn.dataset.originalText) {
                            btn.innerHTML = btn.dataset.originalText;
                        }
                    }
                } else {
                    console.error('❌ Function not found for action:', action); // Log error for missing function (per external feedback)
                    console.error('Available functions:', {
                        processOrders: typeof window.processOrders,
                        updateInventory: typeof window.updateInventory,
                        generateReport: typeof window.generateReport,
                        requestedAction: typeof window[action]
                    });
                }
            }, true); // Use capture phase to catch early
            
            console.log('✅ Event delegation listener attached successfully');
            
            // CRITICAL: Add direct button test listeners as backup
            // This will help us verify if buttons are clickable at all
            var testButtons = document.querySelectorAll('.card-btn[data-action]');
            console.log('🔍 Found buttons for direct testing:', testButtons.length);
            testButtons.forEach(function(btn, index) {
                var action = btn.getAttribute('data-action');
                console.log('🔍 Button ' + index + ':', {
                    action: action,
                    disabled: btn.disabled,
                    className: btn.className
                });
                
                // Add direct click listener as backup test
                btn.addEventListener('click', function(e) {
                    console.log('🔍 DIRECT BUTTON LISTENER FIRED for:', action);
                    console.log('🔍 Direct listener details:', {
                        action: action,
                        disabled: btn.disabled,
                        defaultPrevented: e.defaultPrevented,
                        propagationStopped: false
                    });
                }, true); // Capture phase
            });
            
        });
        // ============================================================================
        // END ROBUST BUTTON EVENT HANDLING
        // ============================================================================
        
// Keyboard shortcuts for power users
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + 1 = Process Orders
            if ((e.ctrlKey || e.metaKey) && e.key === '1') {
                e.preventDefault();
                {% if has_access %}
                var btn = document.querySelector('.card-btn[onclick*="processOrders"]');
                if (btn) processOrders(btn);
                {% else %}
                showSubscribePrompt();
                {% endif %}
            }
            // Ctrl/Cmd + 2 = Check Inventory
            if ((e.ctrlKey || e.metaKey) && e.key === '2') {
                e.preventDefault();
                {% if has_access %}
                var btn = document.querySelector('.card-btn[onclick*="updateInventory"]');
                if (btn) updateInventory(btn);
                {% else %}
                showSubscribePrompt();
                {% endif %}
            }
            // Ctrl/Cmd + 3 = Generate Report
            if ((e.ctrlKey || e.metaKey) && e.key === '3') {
                e.preventDefault();
                {% if has_access %}
                var btn = document.querySelector('.card-btn[onclick*="generateReport"]');
                if (btn) generateReport(btn);
                {% else %}
                showSubscribePrompt();
                {% endif %}
            }
        });
        
        // Track page views (if analytics is set up)
        if (typeof gtag !== 'undefined') {
            gtag('event', 'page_view', {
                'page_title': 'Dashboard',
                'page_location': window.location.href
            });
        }
        
        // CRITICAL: Preserve shop and host parameters when clicking links in embedded mode
        // This ensures navigation doesn't lose the embedded context
        (function() {
            if (window.isEmbedded) {
                var urlParams = new URLSearchParams(window.location.search);
                var shop = urlParams.get('shop');
                var host = urlParams.get('host');
                
                // Intercept all link clicks and preserve shop/host parameters
                document.addEventListener('click', function(e) {
                    var target = e.target;
                    // Find the closest anchor tag
                    while (target && target.tagName !== 'A') {
                        target = target.parentElement;
                    }
                    
                    if (target && target.tagName === 'A' && target.href) {
                        var href = target.href;
                        // CRITICAL: For embedded mode, convert relative URLs to absolute URLs
                        // This prevents Shopify from interpreting them as admin paths (404 errors)
                        if (href.startsWith('/') && !href.startsWith('//')) {
                            // Relative URL - convert to absolute using APP_URL or current origin
                            var appUrl = '{{ APP_URL or "" }}' || window.location.origin;
                            href = appUrl + href;
                            target.href = href; // Update immediately
                        }
                        // Only process internal links (absolute URLs to our app)
                        if (href.startsWith(window.location.origin) || (href.startsWith('https://') && href.includes('employeesuite-production.onrender.com'))) {
                            try {
                                var url = new URL(href);
                                // Preserve shop and host if they exist in current URL
                                if (shop && !url.searchParams.has('shop')) {
                                    url.searchParams.set('shop', shop);
                                }
                                if (host && !url.searchParams.has('host')) {
                                    url.searchParams.set('host', host);
                                }
                                // Update the href with full absolute URL
                                target.href = url.toString();
                            } catch (err) {
                                // If URL parsing fails, try simple string manipulation
                                if (shop || host) {
                                    var separator = href.includes('?') ? '&' : '?';
                                    var params = [];
                                    if (shop && !href.includes('shop=')) {
                                        params.push('shop=' + encodeURIComponent(shop));
                                    }
                                    if (host && !href.includes('host=')) {
                                        params.push('host=' + encodeURIComponent(host));
                                    }
                                    if (params.length > 0) {
                                        target.href = href + separator + params.join('&');
                                    }
                                }
                            }
                        }
                    }
                }, true); // Use capture phase to catch all clicks
            }
        })();
    </script>

    <footer style="margin-top: 64px; padding: 32px 24px; border-top: 1px solid #e1e3e5; text-align: center; background: #ffffff;">
        <div style="max-width: 1200px; margin: 0 auto;">
            <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; font-size: 14px; margin-bottom: 16px;">
                <a href="/faq" style="color: #6d7175; text-decoration: none; font-weight: 400; transition: color 0.15s;">FAQ</a>
                <span style="color: #e1e3e5;">|</span>
                <a href="/privacy" style="color: #6d7175; text-decoration: none; font-weight: 400; transition: color 0.15s;">Privacy Policy</a>
                <span style="color: #e1e3e5;">|</span>
                <a href="/terms" style="color: #6d7175; text-decoration: none; font-weight: 400; transition: color 0.15s;">Terms of Service</a>
            </div>
            <div style="color: #8c9196; font-size: 13px; font-weight: 400;">
                © 2025 Employee Suite. All rights reserved.
            </div>
        </div>
    </footer>
</body>
</html>
"""

@app.route('/favicon.ico')
def favicon():
    """Handle favicon requests - return 204 No Content to prevent 404/500 errors"""
    from flask import Response
    # Return 204 No Content - browser will stop requesting favicon
    return Response(status=204)

@app.route('/')
def home():
    """Home page - CRITICAL: Must render HTML, never redirect for embedded apps"""
    # Check if this is an embedded app request from Shopify
    shop = request.args.get('shop')
    embedded = request.args.get('embedded')
    host = request.args.get('host')
    
    # Check Referer header as Shopify sends requests from admin.shopify.com
    referer = request.headers.get('Referer', '')
    is_from_shopify_admin = 'admin.shopify.com' in referer or '.myshopify.com' in referer
    
    # CRITICAL: For embedded apps, ALWAYS render dashboard - NEVER redirect
    # Redirects break iframes. Just render the dashboard HTML.
    # IMPORTANT: When Shopify first loads the app, it might not have shop/host params yet
    # But the referer will be from admin.shopify.com, so we detect that
    is_embedded = embedded == '1' or shop or host or is_from_shopify_admin
    
    # CRITICAL: If we're being loaded in an iframe from Shopify admin, ALWAYS treat as embedded
    # Even without params, Shopify will add them via App Bridge
    if not is_embedded and is_from_shopify_admin:
        is_embedded = True
    
    if is_embedded:
        # For embedded apps, check if store is connected
        from models import ShopifyStore
        store = None
        user = None
        if shop:
            # DO NOT call db.session.remove() before query - let pool_pre_ping handle validation
            try:
                store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
            except BaseException:
                try:
                    db.session.rollback()
                except Exception:
                    pass
                finally:
                    # Removed db.session.remove() - causes segfaults
                    pass
                store = None
            if store and hasattr(store, 'user') and store.user:
                user = store.user
        
        # CRITICAL: For embedded apps, DON'T use cookies (Safari blocks them)
        # Session tokens handle all authentication - cookies are unreliable in iframes
        # We'll get user info from session tokens in API calls, not from Flask-Login cookies
        
        # For embedded apps, ALWAYS render dashboard - don't check Flask-Login
        # Flask-Login sessions don't work in iframes, but session tokens do
        # CRITICAL: Always render HTML for embedded apps, never redirect
        if True:  # Always render for embedded apps
            # render_template_string is already imported at top of file
            
            # For embedded apps, get user info from store (if connected)
            # Session tokens will verify this in API calls
            if user:
                # Store is connected - use user info for template
                has_access = user.has_access()
                trial_active = user.is_trial_active()
                days_left = (user.trial_ends_at - datetime.utcnow()).days if trial_active else 0
                is_subscribed = user.is_subscribed
                user_id = user.id
            else:
                # Store not connected yet - show connect prompt
                # Session tokens will handle auth once store is connected
                has_access = False
                trial_active = False
                days_left = 0
                is_subscribed = False
                user_id = None
            
            from models import ShopifyStore
            has_shopify = False
            if user_id:
                # DO NOT call db.session.remove() before query - let pool_pre_ping handle validation
                try:
                    has_shopify = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first() is not None
                except BaseException:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                    finally:
                        try:
                            db.session.remove()
                        except Exception:
                            pass
                    has_shopify = False
                except BaseException:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                    finally:
                        try:
                            db.session.remove()
                        except Exception:
                            pass
                    has_shopify = False
            elif shop:
                # Check if store exists even without user auth
                # DO NOT call db.session.remove() before query - let pool_pre_ping handle validation
                try:
                    has_shopify = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first() is not None
                except BaseException:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                    finally:
                        # Removed db.session.remove() - causes segfaults
                        pass
                    has_shopify = False
                except BaseException:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                    finally:
                        # Removed db.session.remove() - causes segfaults
                        pass
                    has_shopify = False
            
            # Skip slow API calls for embedded apps - just show empty stats
            # This prevents the page from hanging while waiting for Shopify API
            quick_stats = {'has_data': False, 'pending_orders': 0, 'total_products': 0, 'low_stock_items': 0}
            # Don't fetch quick stats on initial load - let the user click buttons to load data
            # This makes the page load instantly
            
            shop_domain = shop or ''
            if has_shopify and user_id:
                # DO NOT call db.session.remove() before query - let pool_pre_ping handle validation
                try:
                    store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
                except BaseException:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                    finally:
                        # Removed db.session.remove() - causes segfaults
                        pass
                    store = None
                if store and hasattr(store, 'shop_url') and store.shop_url:
                    shop_domain = store.shop_url
            elif shop:
                # DO NOT call db.session.remove() before query - let pool_pre_ping handle validation
                try:
                    store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
                except BaseException:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                    finally:
                        # Removed db.session.remove() - causes segfaults
                        pass
                    store = None
                if store and hasattr(store, 'shop_url') and store.shop_url:
                    shop_domain = store.shop_url
            
            # CRITICAL: Pass host parameter to template for App Bridge initialization
            host_param = request.args.get('host', '')
            shop_param = shop_domain or shop or request.args.get('shop', '')
            
            APP_URL = os.getenv('APP_URL', request.url_root.rstrip('/'))
            return render_template_string(DASHBOARD_HTML, 
                                         trial_active=trial_active, 
                                         days_left=days_left, 
                                         is_subscribed=is_subscribed, 
                                         has_shopify=has_shopify, 
                                         has_access=has_access,
                                         quick_stats=quick_stats,
                                         shop=shop_param,
                                         shop_domain=shop_domain,
                                         SHOPIFY_API_KEY=os.getenv('SHOPIFY_API_KEY', ''),
                                         APP_URL=APP_URL,
                                         host=host_param)
        else:
            # Not logged in - for embedded apps, render dashboard with connect prompt
            # DON'T redirect - just show the dashboard with a connect button
            # This prevents iframe breaking
            logger.info(f"Store not connected for embedded app: {shop}, showing dashboard with connect prompt")
            
            # Render dashboard with safe defaults (no auth required)
            # render_template_string is already imported at top of file
            has_access = False
            trial_active = False
            days_left = 0
            is_subscribed = False
            has_shopify = False
            quick_stats = {'has_data': False, 'pending_orders': 0, 'total_products': 0, 'low_stock_items': 0}
            shop_domain = shop or ''
            
            # CRITICAL: Pass host parameter to template for App Bridge initialization
            host_param = request.args.get('host', '')
            
            APP_URL = os.getenv('APP_URL', request.url_root.rstrip('/'))
            return render_template_string(DASHBOARD_HTML, 
                                         trial_active=trial_active, 
                                         days_left=days_left, 
                                         is_subscribed=is_subscribed, 
                                         has_shopify=has_shopify, 
                                         has_access=has_access,
                                         quick_stats=quick_stats,
                                         shop=shop_param,
                                         shop_domain=shop_domain,
                                         SHOPIFY_API_KEY=os.getenv('SHOPIFY_API_KEY', ''),
                                         APP_URL=APP_URL,
                                         host=host_param)
    
    # Regular (non-embedded) request handling
    if current_user.is_authenticated:
        # If user is authenticated, always go to dashboard (even if embedded params missing)
        # Check if we have embedded params to preserve them
        shop_param = request.args.get('shop')
        host_param = request.args.get('host')
        dashboard_url = url_for('dashboard')
        if shop_param:
            dashboard_url += f'?shop={shop_param}'
            if host_param:
                dashboard_url += f'&host={host_param}&embedded=1'
        return safe_redirect(dashboard_url, shop=shop_param, host=host_param)
    
    # Check if this might be an embedded request that lost its params
    # If referer is from Shopify admin, treat as embedded
    if is_from_shopify_admin:
        # Render dashboard for embedded apps even without explicit params
        # render_template_string is already imported at top of file
        # CRITICAL: Pass host parameter to template for App Bridge initialization
        host_param = request.args.get('host', '')
        shop_param = shop or request.args.get('shop', '')
        APP_URL = os.getenv('APP_URL', request.url_root.rstrip('/'))
        
        return render_template_string(DASHBOARD_HTML, 
                                     trial_active=False, 
                                     days_left=0, 
                                     is_subscribed=False, 
                                     has_shopify=False, 
                                     has_access=False,
                                     quick_stats={'has_data': False, 'pending_orders': 0, 'total_products': 0, 'low_stock_items': 0},
                                     shop=shop_param,
                                     shop_domain=shop_param,
                                     SHOPIFY_API_KEY=os.getenv('SHOPIFY_API_KEY', ''),
                                     APP_URL=APP_URL,
                                     host=host_param)
    
    # For standalone access, redirect to Shopify OAuth install instead of login
    # OAuth users don't have passwords, so login page won't work for them
    # Show a page that explains they need to install via Shopify
    # render_template_string is already imported at top of file
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Employee Suite - Install via Shopify</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f6f6f7;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 8px;
                padding: 48px;
                max-width: 500px;
                text-align: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            h1 {
                font-size: 28px;
                font-weight: 600;
                color: #202223;
                margin-bottom: 16px;
            }
            p {
                font-size: 15px;
                color: #6d7175;
                line-height: 1.6;
                margin-bottom: 32px;
            }
            .btn {
                display: inline-block;
                background: #008060;
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                text-decoration: none;
                font-weight: 500;
                font-size: 14px;
                transition: background 0.15s;
            }
            .btn:hover {
                background: #006e52;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Install Employee Suite</h1>
            <p>This app is designed to be installed through the Shopify App Store. Please install it from your Shopify admin panel.</p>
            <p style="font-size: 14px; color: #8c9196; margin-top: 24px;">If you're a developer, you can also connect your store manually via Settings after logging in.</p>
            <a href="/settings/shopify" class="btn" style="margin-top: 8px;">Go to Settings</a>
        </div>
    </body>
    </html>
    """)

# Icon is served via Flask static file serving automatically

@app.route('/dashboard')
def dashboard():
    # Check if this is an embedded request (from Referer or params)
    referer = request.headers.get('Referer', '')
    is_from_shopify_admin = 'admin.shopify.com' in referer or 'myshopify.com' in referer
    shop = request.args.get('shop')
    host = request.args.get('host')
    is_embedded = request.args.get('embedded') == '1' or shop or host or is_from_shopify_admin
    
    # CRITICAL: If embedded but no shop param, try to extract from Referer
    if is_embedded and not shop and is_from_shopify_admin:
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(referer)
            # Try extracting from netloc (e.g., employee-suite.myshopify.com)
            if 'myshopify.com' in parsed.netloc:
                shop = parsed.netloc.split('.')[0] + '.myshopify.com'
                logger.info(f"Extracted shop from Referer netloc: {shop}")
            # Try extracting from path (e.g., /store/employee-suite/...)
            elif '/store/' in parsed.path:
                shop_name = parsed.path.split('/store/')[1].split('/')[0]
                shop = f"{shop_name}.myshopify.com"
                logger.info(f"Extracted shop from Referer path: {shop}")
            # Try extracting from query params in Referer
            elif parsed.query:
                query_params = parse_qs(parsed.query)
                if 'shop' in query_params:
                    shop = query_params['shop'][0]
                    logger.info(f"Extracted shop from Referer query: {shop}")
        except Exception as e:
            logger.warning(f"Failed to extract shop from Referer: {e}")
            pass
    
    
    # CRITICAL: For embedded apps without shop, show install message
    # But don't redirect - just show a helpful message
    if is_embedded and not shop:
        logger.warning(f"Embedded app request but no shop param found - showing install message")
        # Can't redirect to OAuth without shop, show install message
        # render_template_string is already imported at top of file
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Install Required - Employee Suite</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background: #f6f6f7; padding: 20px; }
                .container { text-align: center; max-width: 500px; }
                h1 { font-size: 20px; font-weight: 600; color: #202223; margin-bottom: 16px; }
                p { font-size: 14px; color: #6d7175; line-height: 1.6; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Installation Required</h1>
                <p>Please install Employee Suite from your Shopify admin panel to continue.</p>
            </div>
        </body>
        </html>
        """), 400
    
    # For embedded apps, allow access without strict auth (App Bridge handles it)
    # For regular requests without auth, redirect to home (which handles auth properly)
    if not is_embedded and not current_user.is_authenticated:
        # Redirect to home instead of login - home route handles both embedded and standalone properly
        return redirect(url_for('home'))
    
    # If embedded but no session/store found, redirect to OAuth (Shopify's embedded auth flow)
    if is_embedded and shop and not current_user.is_authenticated:
        from models import ShopifyStore, db
        store = None
        # Check if store exists and is connected
        try:
            store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        
        # If no active store found or store is not connected, redirect to OAuth install flow
        # CRITICAL: Use App Bridge redirect to avoid "accounts.shopify.com refused to connect" error
        if not store or not store.is_connected():
            logger.info(f"Embedded app - no active store found for {shop}, redirecting to OAuth via App Bridge")
            from urllib.parse import quote
            install_url = f"/install?shop={quote(shop)}" + (f"&host={quote(host)}" if host else "")
            # Render HTML page that uses App Bridge to redirect in top-level window
            return render_template_string(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Connecting Store - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
    <script>
(function() {{
            var host = '{host or ''}';
            var apiKey = '{os.getenv("SHOPIFY_API_KEY", "")}';
            var installUrl = '{install_url}';
            var attempts = 0;
            var maxAttempts = 100;
            
            function redirectToOAuth() {{
                attempts++;
                var AppBridge = window['app-bridge'] || window['ShopifyAppBridge'] || window.appBridge;
                
                if (AppBridge && host && apiKey && AppBridge.default && AppBridge.actions && AppBridge.actions.Redirect) {{
                    try {{
                        var app = AppBridge.default({{ apiKey: apiKey, host: host }});
                        var Redirect = AppBridge.actions.Redirect;
                        var redirect = Redirect.create(app);
                        // CRITICAL: Use REMOTE action to redirect top-level window, not iframe
                        redirect.dispatch(Redirect.Action.REMOTE, installUrl);
                        console.log('✅ App Bridge REMOTE redirect dispatched to:', installUrl);
                        return;
                    }} catch (e) {{
                        console.error('App Bridge redirect error:', e);
                    }}
                }}
                
                // Fallback: show button with target="_top" if App Bridge not available
                if (attempts < maxAttempts) {{
                    setTimeout(redirectToOAuth, 100);
                }} else {{
                    console.warn('⚠️ App Bridge not available, showing button with target="_top"');
                    // CRITICAL: Never use programmatic redirects - show button with target="_top" instead
                    // This prevents "accounts.shopify.com refused to connect" error
                    // Use string concatenation to build HTML (not template literals to avoid f-string conflicts)
                    var html = '<div style="padding: 40px; text-align: center; font-family: -apple-system, BlinkMacSystemFont, \\'Segoe UI\\', Roboto, sans-serif; background: #fff; border-radius: 8px; max-width: 500px; margin: 40px auto; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">';
                    html += '<h2 style="color: #202223; margin-bottom: 16px; font-size: 20px;">Connect Your Shopify Store</h2>';
                    html += '<p style="color: #6d7175; margin-bottom: 24px; line-height: 1.5;">Click the button below to authorize the connection. This will open in the top-level window.</p>';
                    html += '<a href="' + installUrl + '" target="_top" style="display: inline-block; background: #008060; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px; transition: background 0.2s;">Continue to Shopify Authorization →</a>';
                    html += '</div>';
                    document.body.innerHTML = html;
                }}
            }}
            
            // Start redirect attempt
            redirectToOAuth();
        }})();
    </script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            background: #f6f6f7;
        }}
        .container {{
            text-align: center;
            padding: 40px 24px;
        }}
        .spinner {{
            width: 24px;
            height: 24px;
            border: 2px solid #e1e3e5;
            border-top: 2px solid #008060;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 24px;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        .title {{
            font-size: 18px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 8px;
        }}
        .message {{
            font-size: 14px;
            color: #6d7175;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="spinner"></div>
        <div class="title">Connecting to Shopify</div>
        <div class="message">Redirecting you to authorize the connection...</div>
    </div>
</body>
</html>""")
    
    # render_template_string is already imported at top of file - DO NOT import locally
    
    # For embedded requests, always render - never redirect
    # This prevents iframe breaking
    """Dashboard - accessible to all authenticated users, shows subscribe prompt if no access"""
    
    # Handle case where user might not be authenticated (for embedded apps)
    # CRITICAL: Check authentication safely - current_user might not be loaded yet
    try:
        user_authenticated = current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False
    except Exception:
        user_authenticated = False
    
    if user_authenticated:
        try:
            has_access = current_user.has_access()
            trial_active = current_user.is_trial_active()
            days_left = (current_user.trial_ends_at - datetime.utcnow()).days if trial_active else 0
            is_subscribed = current_user.is_subscribed
        except Exception as e:
            logger.error(f"Error accessing user properties: {e}", exc_info=True)
            has_access = False
            trial_active = False
            days_left = 0
            is_subscribed = False
    else:
        # Embedded app without auth - show limited view
        has_access = False
        trial_active = False
        days_left = 0
        is_subscribed = False
    
    # Check if user has connected Shopify - OPTIMIZED: Single query instead of multiple
    from models import ShopifyStore
    store = None
    has_shopify = False
    shop_domain = shop or ''
    
    # OPTIMIZED: Single database query to get store (reduces from 3-4 queries to 1)
    try:
        if user_authenticated:
            # Query by user_id first (most common case)
            store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
        elif shop:
            # Fallback: query by shop_url for embedded apps
            store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
        
        if store:
            has_shopify = True
            shop_domain = store.shop_url if hasattr(store, 'shop_url') and store.shop_url else shop_domain
    except BaseException as e:
        # CRITICAL: Only rollback on exception, DO NOT call db.session.remove() - it can cause segfaults
        try:
            db.session.rollback()
        except Exception:
            pass
        # DO NOT call db.session.remove() here - it corrupts connection state and causes segfaults
        store = None
        has_shopify = False
    
    # Skip slow API calls on dashboard load - just show empty stats
    # This prevents the page from hanging while waiting for Shopify API
    # Users can click buttons to load data when they need it
    quick_stats = {'has_data': False, 'pending_orders': 0, 'total_products': 0, 'low_stock_items': 0}
    
    # Store shop in session for API calls (if shop parameter is present)
    if shop_domain:
        from flask import session
        session['current_shop'] = shop_domain
        session.permanent = True
        logger.info(f"Stored shop in session: {shop_domain} for user {current_user.id if user_authenticated else 'anonymous'}")
    
    # CRITICAL: Pass host parameter to template for App Bridge initialization
    host_param = request.args.get('host', '')
    shop_param = shop_domain or shop or request.args.get('shop', '')
    
    
    APP_URL = os.getenv('APP_URL', request.url_root.rstrip('/'))
    return render_template_string(DASHBOARD_HTML, 
                                 trial_active=trial_active, 
                                 days_left=days_left, 
                                 is_subscribed=is_subscribed, 
                                 has_shopify=has_shopify, 
                                 has_access=has_access,
                                 quick_stats=quick_stats,
                                 shop=shop_param,
                                 shop_domain=shop_domain,
                                 SHOPIFY_API_KEY=os.getenv('SHOPIFY_API_KEY', ''),
                                 APP_URL=APP_URL,
                                 host=host_param)


@app.route('/cron/send-trial-warnings', methods=['GET', 'POST'])
def cron_trial_warnings():
    """Endpoint for external cron service"""
    import os
    secret = request.args.get('secret') or request.form.get('secret')
    
    if secret != os.getenv('CRON_SECRET'):
        return jsonify({"error": "Unauthorized"}), 401
    
    from cron_jobs import send_trial_warnings
    try:
        send_trial_warnings()
        return jsonify({"success": True, "message": "Warnings sent"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cron/database-backup', methods=['GET', 'POST'])
def cron_database_backup():
    """Endpoint for automated database backups via external cron service"""
    secret = request.args.get('secret') or request.form.get('secret')
    
    if secret != os.getenv('CRON_SECRET'):
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        from database_backup import run_backup
        result = run_backup()
        
        if result['success']:
            logger.info(f"Automated backup completed: {result['backup_file']}")
            return jsonify({
                "success": True,
                "message": "Backup completed successfully",
                "backup_file": result['backup_file'],
                "s3_key": result['s3_key'],
                "timestamp": result['timestamp']
            }), 200
        else:
            logger.error(f"Automated backup failed: {result.get('error')}")
            return jsonify({
                "success": False,
                "error": result.get('error', 'Unknown error'),
                "timestamp": result.get('timestamp')
            }), 500
            
    except Exception as e:
        logger.error(f"Backup cron endpoint error: {e}", exc_info=True)
        return jsonify({"error": str(e), "success": False}), 500

def is_debug_enabled():
    """Check if debug endpoints should be enabled"""
    env = os.getenv('ENVIRONMENT', 'production')
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    return env == 'development' or debug

@app.route('/api-key-info')
def api_key_info():
    """Debug endpoint - ONLY works in development"""
    if not is_debug_enabled():
        return jsonify({"error": "Not available in production"}), 403
    
    api_key = os.getenv('SHOPIFY_API_KEY', 'NOT_SET')
    api_secret = os.getenv('SHOPIFY_API_SECRET', 'NOT_SET')
    
    response = {
        'api_key': {
            'status': 'SET' if api_key != 'NOT_SET' and api_key else 'NOT_SET',
            'preview': api_key[:8] + '...' if api_key and api_key != 'NOT_SET' and len(api_key) >= 8 else 'N/A',
            'length': len(api_key) if api_key and api_key != 'NOT_SET' else 0,
        },
        'api_secret': {
            'status': 'SET' if api_secret != 'NOT_SET' and api_secret else 'NOT_SET',
            'preview': api_secret[:8] + '...' if api_secret and api_secret != 'NOT_SET' and len(api_secret) >= 8 else 'N/A',
            'length': len(api_secret) if api_secret and api_secret != 'NOT_SET' else 0
        }
    }
    # REMOVED: full API key exposure
    return jsonify(response)

@app.route('/test-shopify-route')
def test_shopify_route():
    """Test route to verify app is picking up changes"""
    return jsonify({"status": "ok", "message": "App is picking up changes", "shopify_routes": [str(rule) for rule in app.url_map.iter_rules() if 'shopify' in str(rule)]})

@app.route('/debug-routes')
def debug_routes():
    """Debug endpoint - ONLY works in development"""
    if not is_debug_enabled():
        return jsonify({"error": "Not available in production"}), 403
    
    all_routes = [{"rule": str(rule.rule), "endpoint": rule.endpoint, "methods": list(rule.methods)} for rule in app.url_map.iter_rules()]
    shopify_routes = [r for r in all_routes if 'shopify' in r['rule'].lower()]
    return jsonify({
        "total_routes": len(all_routes),
        "shopify_routes": shopify_routes,
        "shopify_routes_count": len(shopify_routes),
        "all_routes": all_routes[:50]  # First 50 routes
    })

@app.route('/health')
def health():
    """Health check endpoint for monitoring"""
    from datetime import datetime
    from performance import get_cache_stats
    import sys
    
    checks = {}
    overall_status = "healthy"
    
    # Cache check
    try:
        cache_stats = get_cache_stats()
        checks['cache'] = {
            "entries": cache_stats.get('entries', 0),
            "max_entries": cache_stats.get('max_entries', 100),
            "size_mb": cache_stats.get('size_mb', 0.0),
            "status": "operational"
        }
    except Exception as e:
        checks['cache'] = {"error": str(e), "status": "error"}
        overall_status = "unhealthy"
    
    # Database check
    try:
        db.session.execute(db.text('SELECT 1'))
        checks['database'] = {"status": "connected"}
    except Exception as e:
        checks['database'] = {"error": str(e), "status": "disconnected"}
        overall_status = "unhealthy"
    
    # Environment check
    try:
        import flask
        checks['environment'] = {
            "environment": os.getenv('ENVIRONMENT', 'unknown'),
            "flask_version": flask.__version__,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        }
    except Exception as e:
        checks['environment'] = {"error": str(e), "status": "error"}
    
    # Memory check (optional - psutil might not be available)
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        checks['memory'] = {
            "rss_mb": round(memory_info.rss / (1024 * 1024), 2),
            "vms_mb": round(memory_info.vms / (1024 * 1024), 2),
            "status": "operational"
        }
    except ImportError:
        checks['memory'] = {
            "note": "psutil not available (optional)",
            "status": "unknown"
        }
    except Exception as e:
        checks['memory'] = {"error": str(e), "status": "error"}
    
    # Determine overall database status for backward compatibility
    database_status = "connected" if checks.get('database', {}).get('status') == 'connected' else "disconnected"
    
    return jsonify({
        "status": overall_status,
        "service": "Employee Suite",
        "version": "2.0",
        "database": database_status,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }), 200 if overall_status == "healthy" else 500

@app.route('/api/log_error', methods=['POST'])
def log_error():
    """API endpoint to receive JavaScript errors from frontend"""
    try:
        from flask import request, jsonify
        error_data = request.get_json()
        
        if not error_data:
            return jsonify({'success': False, 'error': 'No error data provided'}), 400
        
        # Log the JavaScript error with comprehensive details
        error_type = error_data.get('error_type', 'UnknownError')
        error_message = error_data.get('error_message', 'Unknown error')
        error_location = error_data.get('error_location', 'unknown')
        stack_trace = error_data.get('stack_trace', 'No stack trace')
        
        # Add request context
        full_error_data = {
            **error_data,
            'request_url': request.url,
            'request_method': request.method,
            'remote_addr': request.remote_addr,
            'referer': request.headers.get('Referer'),
        }
        
        log_comprehensive_error(
            f'JS_{error_type}',
            error_message,
            error_location,
            full_error_data,
            None  # No Python exc_info for JS errors
        )
        
        return jsonify({'success': True, 'message': 'Error logged'}), 200
        
    except Exception as e:
        # Even error logging can fail - log it
        log_comprehensive_error(
            'ErrorLoggingFailed',
            str(e),
            'log_error endpoint',
            {'original_error_data': str(request.get_json()) if request.is_json else None},
            sys.exc_info()
        )
        return jsonify({'success': False, 'error': 'Failed to log error'}), 500

@app.route('/api/docs')
def api_docs():
    """API documentation endpoint"""
    return redirect('https://github.com/vyndigital-cloud/EmployeeSuite-Production/blob/main/API_DOCUMENTATION.md')

def get_authenticated_user():
    """
    Get authenticated user from either Flask-Login or Shopify session token.
    Returns (user, error_response) tuple. If user is None, error_response contains the error.
    """
    # Try Flask-Login first (for standalone access)
    if current_user.is_authenticated:
        logger.debug(f"User authenticated via Flask-Login: {current_user.id}")
        return current_user, None
    
    # Try session token (for embedded apps)
    auth_header = request.headers.get('Authorization', '')
    logger.debug(f"Auth header present: {bool(auth_header)}, starts with Bearer: {auth_header.startswith('Bearer ')}")
    if auth_header.startswith('Bearer '):
        try:
            token = auth_header.split(' ')[1] if ' ' in auth_header else None
            if not token:
                return None, (jsonify({'error': 'Invalid token format', 'success': False}), 401)
            
            # Properly verify JWT token with full validation
            import jwt
            
            # CRITICAL: Check environment variables exist
            api_secret = os.getenv('SHOPIFY_API_SECRET')
            api_key = os.getenv('SHOPIFY_API_KEY')
            
            if not api_secret:
                logger.warning("SHOPIFY_API_SECRET not set - cannot verify session token")
                return None, (jsonify({'error': 'Server configuration error', 'success': False}), 500)
            
            if not api_key:
                logger.warning("SHOPIFY_API_KEY not set - cannot verify session token")
                return None, (jsonify({'error': 'Server configuration error', 'success': False}), 500)
            
            payload = jwt.decode(
                token,
                api_secret,
                algorithms=['HS256'],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["iss", "dest", "aud", "sub", "exp", "nbf", "iat"]
                }
            )
            
            # Verify audience matches API key
            if payload.get('aud') != api_key:
                logger.warning(f"Invalid audience in session token: {payload.get('aud')}")
                return None, (jsonify({'error': 'Invalid token', 'success': False}), 401)
            
            # Extract shop domain
            dest = payload.get('dest', '')
            if not dest or not dest.endswith('.myshopify.com'):
                logger.warning(f"Invalid destination in session token: {dest}")
                return None, (jsonify({'error': 'Invalid token', 'success': False}), 401)
            
            # CRITICAL: Safe string splitting - handle edge cases
            try:
                cleaned_dest = dest.replace('https://', '').replace('http://', '')
                shop_domain = cleaned_dest.split('/')[0] if '/' in cleaned_dest else cleaned_dest
                if not shop_domain:
                    raise ValueError("Empty shop domain")
            except (IndexError, AttributeError, ValueError) as e:
                logger.warning(f"Error parsing shop domain from dest '{dest}': {e}")
                return None, (jsonify({'error': 'Invalid token format', 'success': False}), 401)
            
            # Find user from shop - CRITICAL: Protect against segfaults
            # DO NOT call db.session.remove() - let pool_pre_ping validate connections
            from models import ShopifyStore, db
            store = None
            try:
                store = ShopifyStore.query.filter_by(shop_url=shop_domain, is_active=True).first()
            except BaseException as db_error:
                logger.error(f"Database error in get_authenticated_user: {type(db_error).__name__}: {str(db_error)}", exc_info=True)
                try:
                    db.session.rollback()
                except Exception:
                    pass
                finally:
                    try:
                        db.session.remove()
                    except Exception:
                        pass
                return None, (jsonify({'error': 'Database connection error', 'success': False, 'action': 'retry'}), 500)
            
            if store and store.user:
                logger.info(f"✅ Session token verified - user {store.user.id} from shop {shop_domain}")
                return store.user, None
            else:
                logger.warning(f"❌ No store found for shop: {shop_domain}")
                return None, (jsonify({
                    'error': 'Your store is not connected. Please install the app from your Shopify admin.',
                    'success': False,
                    'action': 'install',
                    'message': 'To get started, install Employee Suite from your Shopify admin panel.'
                }), 404)
                
        except jwt.ExpiredSignatureError:
            logger.warning("Expired session token")
            return None, (jsonify({
                'error': 'Your session has expired. Please refresh the page.',
                'success': False,
                'action': 'refresh',
                'message': 'This usually happens when the page has been open for a while. Refreshing will restore your session.'
            }), 401)
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid session token: {e}")
            return None, (jsonify({
                'error': 'Unable to verify your session. Please refresh the page.',
                'success': False,
                'action': 'refresh',
                'message': 'If the problem persists, try closing and reopening the app from your Shopify admin.'
            }), 401)
        except Exception as e:
            logger.error(f"Error verifying session token: {e}", exc_info=True)
            return None, (jsonify({
                'error': 'We encountered an issue verifying your session. Please try again.',
                'success': False,
                'action': 'retry',
                'message': 'If this continues, please refresh the page or contact support.'
            }), 401)
    
    # No authentication found
    return None, (jsonify({
        'error': 'Please sign in to continue.',
        'success': False,
        'action': 'login',
        'message': 'You need to be signed in to use this feature. If you\'re using the app from Shopify admin, try refreshing the page.'
    }), 401)

@app.route('/api/process_orders', methods=['GET', 'POST'])
def api_process_orders():
    """Process orders endpoint with enhanced logging"""
    # #region agent log
    try:
        import json
        import time
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"app.py:api_process_orders","message":"API endpoint entry","data":{"method":request.method,"path":request.path,"has_auth":bool(request.headers.get("Authorization")),"has_shop":bool(request.args.get("shop"))},"timestamp":int(time.time()*1000)})+'\n')
    except: pass
    # #endregion
    logger.info('=== PROCESS ORDERS REQUEST START ===')
    logger.info(f'Request method: {request.method}')
    logger.info(f'Request path: {request.path}')
    logger.info(f'Request URL: {request.url}')
    logger.info(f'Request headers: {dict(request.headers)}')
    logger.info(f'Request args: {dict(request.args)}')
    logger.info(f'Has Authorization header: {bool(request.headers.get("Authorization"))}')
    logger.info(f'Has shop parameter: {bool(request.args.get("shop"))}')
    
    
    try:
        # Get authenticated user (supports both Flask-Login and session tokens)
        logger.info('Step 1: Getting authenticated user...')
        user, error_response = get_authenticated_user()
        
        if error_response:
            logger.warning('Step 1 FAILED: Authentication error')
            logger.warning(f'Error response status: {error_response.status_code if hasattr(error_response, "status_code") else "N/A"}')
            return error_response
        
        logger.info(f'Step 1 SUCCESS: User authenticated: {user.email if hasattr(user, "email") else "N/A"}')
        
        # Check access
        logger.info('Step 2: Checking user access...')
        has_access = user.has_access() if user else False
        
        if not has_access:
            logger.warning(f'Step 2 FAILED: User {user.id if hasattr(user, "id") else "N/A"} does not have access')
            return jsonify({
                'error': 'Subscription required',
                'success': False,
                'action': 'subscribe',
                'message': 'Your trial has ended. Subscribe to continue using Employee Suite.',
                'subscribe_url': url_for('billing.subscribe')
            }), 403
        
        logger.info(f'Step 2 SUCCESS: User {user.id if hasattr(user, "id") else "N/A"} has access')
        
        # Store user ID before login_user to avoid recursion issues
        user_id = user.id if hasattr(user, 'id') else getattr(user, 'id', None)
        logger.info(f'Step 3: User ID extracted: {user_id}')
        
        # Temporarily set current_user for process_orders() function
        # (it expects current_user to be set)
        logger.info('Step 4: Logging in user...')
        from flask_login import login_user
        login_user(user, remember=False)
        logger.info('Step 4 SUCCESS: User logged in')
        
        
        logger.info(f'Step 5: Calling process_orders for user {user_id}...')
        # Pass user_id directly to prevent recursion from accessing current_user
        result = process_orders(user_id=user_id)
        logger.info(f'Step 5 SUCCESS: process_orders returned')
        logger.info(f'Result type: {type(result)}, Is dict: {isinstance(result, dict)}')
        if isinstance(result, dict):
            logger.info(f'Result keys: {list(result.keys())}')
            logger.info(f'Result success: {result.get("success", "N/A")}')
            if 'error' in result:
                logger.warning(f'Result contains error: {result.get("error")}')
        
        
        logger.info('=== PROCESS ORDERS REQUEST SUCCESS ===')
        if isinstance(result, dict):
            return jsonify(result)
        else:
            return jsonify({"message": str(result), "success": True})
            
    except MemoryError as e:
        # #region agent log
        try:
            import json
            import time
            with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"app.py:api_process_orders:MemoryError","message":"Memory error exception","data":{"user_id":user_id,"error":str(e)[:200]},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        logger.error(f"Memory error processing orders for user {user_id}: {str(e)}", exc_info=True)
        logger.error("Clearing cache...")
        from performance import clear_cache as clear_perf_cache
        clear_perf_cache()
        logger.error('=== PROCESS ORDERS REQUEST FAILED: Memory Error ===')
        return jsonify({"error": "Memory error - please try again", "success": False}), 500
    except SystemExit:
        # Conditional debug logging
        from debug_utils import debug_log
        debug_log(
            location="app.py:api_process_orders:SystemExit",
            message="SystemExit exception",
            data={"user_id": user_id},
            hypothesis_id="E"
        )
        # Re-raise system exits (like from sys.exit())
        logger.error('=== PROCESS ORDERS REQUEST FAILED: SystemExit ===')
        raise
    except BaseException as e:
        # Conditional debug logging
        from debug_utils import debug_log
        import traceback
        debug_log(
            location="app.py:api_process_orders:BaseException",
            message="BaseException caught",
            data={
                "user_id": user_id,
                "error_type": type(e).__name__,
                "error": str(e)[:200],
                "stack_preview": traceback.format_exc()[:500]
            },
            hypothesis_id="E"
        )
        # Catch all other exceptions including segmentation faults precursors
        logger.error(f"Critical error processing orders for user {user_id}: {type(e).__name__}: {str(e)}", exc_info=True)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        from performance import clear_cache as clear_perf_cache
        try:
            clear_perf_cache()
        except Exception:
            pass
        logger.error('=== PROCESS ORDERS REQUEST FAILED: Critical Error ===')
        return jsonify({"error": "An unexpected error occurred. Please try again or contact support if this persists.", "success": False}), 500

@app.route('/api/update_inventory', methods=['GET', 'POST'])
def api_update_inventory():
    """Update inventory endpoint with enhanced logging"""
    # #region agent log
    try:
        import json
        import time
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"app.py:api_update_inventory","message":"API endpoint entry","data":{"method":request.method,"path":request.path,"has_auth":bool(request.headers.get("Authorization")),"has_shop":bool(request.args.get("shop"))},"timestamp":int(time.time()*1000)})+'\n')
    except: pass
    # #endregion
    logger.info('=== UPDATE INVENTORY REQUEST START ===')
    logger.info(f'Request method: {request.method}')
    logger.info(f'Request path: {request.path}')
    logger.info(f'Request URL: {request.url}')
    logger.info(f'Request headers: {dict(request.headers)}')
    logger.info(f'Request args: {dict(request.args)}')
    logger.info(f'Has Authorization header: {bool(request.headers.get("Authorization"))}')
    logger.info(f'Has shop parameter: {bool(request.args.get("shop"))}')
    
    
    try:
        # Get authenticated user (supports both Flask-Login and session tokens)
        logger.info('Step 1: Getting authenticated user...')
        user, error_response = get_authenticated_user()
        
        if error_response:
            logger.warning('Step 1 FAILED: Authentication error')
            logger.warning(f'Error response status: {error_response.status_code if hasattr(error_response, "status_code") else "N/A"}')
            return error_response
        
        logger.info(f'Step 1 SUCCESS: User authenticated: {user.email if hasattr(user, "email") else "N/A"}')
        
        logger.info('Step 2: Checking user access...')
        has_access = user.has_access() if user else False
        
        if not has_access:
            logger.warning(f'Step 2 FAILED: User {user.id if hasattr(user, "id") else "N/A"} does not have access')
            return jsonify({
                'error': 'Subscription required',
                'success': False,
                'action': 'subscribe',
                'message': 'Your trial has ended. Subscribe to continue using Employee Suite.',
                'subscribe_url': url_for('billing.subscribe')
            }), 403
        
        logger.info(f'Step 2 SUCCESS: User {user.id if hasattr(user, "id") else "N/A"} has access')
        
        # Store user ID before login_user to avoid recursion issues
        user_id = user.id if hasattr(user, 'id') else getattr(user, 'id', None)
        logger.info(f'Step 3: User ID extracted: {user_id}')
        
        # Set current_user for update_inventory() function
        logger.info('Step 4: Logging in user...')
        from flask_login import login_user
        login_user(user, remember=False)
        logger.info('Step 4 SUCCESS: User logged in')
    
        # Import at function level to avoid UnboundLocalError
        logger.info('Step 5: Clearing cache...')
        from performance import clear_cache as clear_perf_cache
        clear_perf_cache('get_products')
        logger.info('Step 5 SUCCESS: Cache cleared')
        
        
        logger.info(f'Step 6: Calling update_inventory for user {user_id}...')
        # Pass user_id directly to prevent recursion from accessing current_user
        result = update_inventory(user_id=user_id)
        logger.info(f'Step 6 SUCCESS: update_inventory returned')
        logger.info(f'Result type: {type(result)}, Is dict: {isinstance(result, dict)}')
        if isinstance(result, dict):
            logger.info(f'Result keys: {list(result.keys())}')
            logger.info(f'Result success: {result.get("success", "N/A")}')
            if 'error' in result:
                logger.warning(f'Result contains error: {result.get("error")}')
        
        
        logger.info('=== UPDATE INVENTORY REQUEST SUCCESS ===')
        if isinstance(result, dict):
            # Store inventory data in session for CSV export
            if result.get('success') and 'inventory_data' in result:
                from flask import session
                session['inventory_data'] = result['inventory_data']
                logger.info('Inventory data stored in session for CSV export')
            return jsonify(result)
        else:
            return jsonify({"success": False, "error": str(result)})
            
    except MemoryError as e:
        logger.error(f"Memory error updating inventory for user {user_id}: {str(e)}", exc_info=True)
        logger.error("Clearing cache...")
        from performance import clear_cache as clear_perf_cache
        clear_perf_cache()
        logger.error('=== UPDATE INVENTORY REQUEST FAILED: Memory Error ===')
        return jsonify({"success": False, "error": "Memory error - please try again"}), 500
    except SystemExit:
        # Re-raise system exits (like from sys.exit())
        logger.error('=== UPDATE INVENTORY REQUEST FAILED: SystemExit ===')
        raise
    except BaseException as e:
        # Catch all other exceptions including segmentation faults precursors
        logger.error(f"Critical error updating inventory for user {user_id}: {type(e).__name__}: {str(e)}", exc_info=True)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        from performance import clear_cache as clear_perf_cache
        try:
            clear_perf_cache()
        except Exception:
            pass
        logger.error('=== UPDATE INVENTORY REQUEST FAILED: Critical Error ===')
        return jsonify({"success": False, "error": "An unexpected error occurred. Please try again or contact support if this persists."}), 500

@app.route('/api/generate_report', methods=['GET', 'POST'])
def api_generate_report():
    """Generate revenue report with detailed crash logging"""
    # #region agent log
    try:
        import json
        import time
        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"app.py:api_generate_report","message":"API endpoint entry","data":{"method":request.method,"path":request.path,"has_auth":bool(request.headers.get("Authorization")),"has_shop":bool(request.args.get("shop"))},"timestamp":int(time.time()*1000)})+'\n')
    except: pass
    # #endregion
    logger.info('=== GENERATE REPORT REQUEST START ===')
    logger.info(f'Request method: {request.method}')
    logger.info(f'Request path: {request.path}')
    logger.info(f'Request URL: {request.url}')
    logger.info(f'Request headers: {dict(request.headers)}')
    logger.info(f'Request args: {dict(request.args)}')
    logger.info(f'Has Authorization header: {bool(request.headers.get("Authorization"))}')
    logger.info(f'Has shop parameter: {bool(request.args.get("shop"))}')
    
    
    user_id = None
    try:
        # Get authenticated user (supports both Flask-Login and session tokens)
        logger.info('Step 1: Getting authenticated user...')
        user, error_response = get_authenticated_user()
        
        if error_response:
            logger.warning('Step 1 FAILED: Authentication error')
            logger.warning(f'Error response status: {error_response.status_code if hasattr(error_response, "status_code") else "N/A"}')
            return error_response
        
        logger.info(f'Step 1 SUCCESS: User authenticated: {user.email if hasattr(user, "email") else "N/A"}')
        
        # Store user ID before login_user to avoid recursion issues
        user_id = user.id if hasattr(user, 'id') else getattr(user, 'id', None)
        logger.info(f'Step 2: User ID extracted: {user_id}')
        
        logger.info('Step 3: Checking user access...')
        has_access = user.has_access() if user else False
        
        if not has_access:
            logger.warning(f'Step 3 FAILED: User {user_id} does not have access')
            return jsonify({
                'error': 'Subscription required',
                'success': False,
                'action': 'subscribe',
                'message': 'Your trial has ended. Subscribe to continue using Employee Suite.',
                'subscribe_url': url_for('billing.subscribe')
            }), 403
        
        logger.info(f'Step 3 SUCCESS: User {user_id} has access')
        
        # Set current_user for generate_report() function
        logger.info('Step 4: Logging in user...')
        from flask_login import login_user
        login_user(user, remember=False)
        logger.info('Step 4 SUCCESS: User logged in')
        
        logger.info(f'Step 5: Preparing to generate report for user {user_id}...')
        
        # Get shop_url from request args, session, or None (will use first active store)
        from flask import session
        shop_url = request.args.get('shop') or session.get('current_shop') or None
        if shop_url:
            logger.info(f'Step 5a: Using shop_url from request/session: {shop_url}')
        else:
            logger.info(f'Step 5a: No shop_url in request/session, will use first active store for user')
        
        # CRITICAL: DO NOT call db.session.remove() here - let SQLAlchemy manage connections
        # Removing sessions before queries can cause segfaults by corrupting connection state
        logger.info('Step 5b: Importing generate_report function...')
        from reporting import generate_report
        logger.info('Step 5b SUCCESS: generate_report function imported')
        
        
        logger.info(f'Step 5c: Calling generate_report(user_id={user_id}, shop_url={shop_url})...')
        data = generate_report(user_id=user_id, shop_url=shop_url)
        logger.info(f'Step 5c SUCCESS: generate_report() returned')
        logger.info(f'Result type: {type(data)}, Is dict: {isinstance(data, dict)}')
        if isinstance(data, dict):
            logger.info(f'Result keys: {list(data.keys())}')
            if 'error' in data:
                logger.warning(f'Result contains error: {data.get("error")}')
            if 'message' in data:
                logger.info(f'Result message: {data.get("message")[:100]}...' if len(str(data.get("message", ""))) > 100 else f'Result message: {data.get("message")}')
        
        if data.get('error') and data['error'] is not None:
            error_html = data['error']
            logger.warning(f'Step 5d: Report generation returned error (handled gracefully)')
            if 'No Shopify store connected' in error_html:
                logger.info(f'Generate report: No store connected for user {user_id}')
            elif 'Permission denied' in error_html or 'missing required permissions' in error_html.lower():
                # This is expected - user needs to reconnect with proper scopes
                logger.info(f'Generate report: Missing permissions for user {user_id} - user will be prompted to reconnect')
            else:
                logger.warning(f'Generate report error for user {user_id}: {error_html[:100]}...')
            # Don't log as error - this is a handled, user-facing error (not a system error)
            # Return HTML directly with 200 status so frontend can render it
            return error_html, 200, {'Content-Type': 'text/html'}
        
        if not data.get('message'):
            logger.warning(f'Step 5d WARNING: No message in report data')
            logger.warning(f'Generate report returned no message for user {user_id}')
            logger.error('=== GENERATE REPORT REQUEST FAILED: No Data ===')
            # Return HTML directly with 200 status so frontend can render it
            return '<h3 class="error">❌ No report data available</h3>', 200, {'Content-Type': 'text/html'}
        
        html = data.get('message', '<h3 class="error">❌ No report data available</h3>')
        logger.info(f'Step 5d: Report HTML generated, length: {len(html)} characters')
        
        from flask import session
        if 'report_data' in data:
            session['report_data'] = data['report_data']
            logger.info('Step 5e: Report data stored in session for CSV export')
        
        logger.info('=== GENERATE REPORT REQUEST SUCCESS ===')
        return html, 200
        
    except MemoryError as e:
        logger.error('=== GENERATE REPORT REQUEST FAILED: Memory Error ===')
        logger.error(f'Error type: {type(e).__name__}')
        logger.error(f'Error message: {str(e)}')
        logger.error(f'Full traceback:\n{traceback.format_exc()}')
        logger.error(f'Memory error generating report for user {user_id} - clearing cache')
        from performance import clear_cache as clear_perf_cache
        clear_perf_cache()
        return jsonify({"success": False, "error": "Memory error - please try again"}), 500
    except SystemExit as e:
        logger.error('=== GENERATE REPORT REQUEST FAILED: SystemExit ===')
        logger.error(f'Error type: {type(e).__name__}')
        logger.error(f'Error message: {str(e)}')
        logger.error(f'Full traceback:\n{traceback.format_exc()}')
        # Re-raise system exits (like from sys.exit())
        raise
    except BaseException as e:
        logger.error('=== GENERATE REPORT REQUEST FAILED: Critical Error ===')
        logger.error(f'Error type: {type(e).__name__}')
        logger.error(f'Error message: {str(e)}')
        logger.error(f'Full traceback:\n{traceback.format_exc()}')
        logger.error(f'User ID: {user_id}')
        logger.error(f'Exception args: {e.args}')
        # Catch all other exceptions including segmentation faults precursors
        logger.error(f'Critical error generating report for user {user_id}: {type(e).__name__}: {str(e)}', exc_info=True)
        from performance import clear_cache as clear_perf_cache
        try:
            clear_perf_cache()
        except Exception:
            pass
        return jsonify({"success": False, "error": "An unexpected error occurred. Please try again or contact support if this persists."}), 500
    except Exception as e:
        logger.error('=== GENERATE REPORT REQUEST FAILED: Exception ===')
        logger.error(f'Error type: {type(e).__name__}')
        logger.error(f'Error message: {str(e)}')
        logger.error(f'Full traceback:\n{traceback.format_exc()}')
        logging.error(f"User ID: {user_id}")
        logging.error("=== END CRASH LOG ===")
        logger.error(f"Error generating report for user {user_id}: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": f"Failed to generate report: {str(e)}"}), 500

# Note: This is a duplicate 404 handler - the main one is at line 286
# Keeping for backward compatibility but routing to main handler
@app.errorhandler(404)
def not_found(error):
    """404 error handler - professional error page (duplicate, routes to main handler)"""
    # Route to main 404 handler which has enhanced logging
    return handle_404(error)
    
    error_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page Not Found - Employee Suite</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, #f5f5f5 0%, #fafafa 100%);
                color: #171717;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                padding: 24px;
            }
            .error-container {
                text-align: center;
                max-width: 500px;
            }
            .error-code {
                font-size: 120px;
                font-weight: 700;
                color: #4a7338;
                line-height: 1;
                margin-bottom: 16px;
            }
            .error-title {
                font-size: 28px;
                font-weight: 600;
                color: #0a0a0a;
                margin-bottom: 12px;
            }
            .error-message {
                font-size: 16px;
                color: #737373;
                margin-bottom: 32px;
                line-height: 1.6;
            }
            .error-actions {
                display: flex;
                gap: 12px;
                justify-content: center;
                flex-wrap: wrap;
            }
            .btn {
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 500;
                text-decoration: none;
                transition: all 0.2s;
                border: none;
                cursor: pointer;
            }
            .btn-primary {
                background: #4a7338;
                color: #fff;
            }
            .btn-primary:hover {
                background: #3a5c2a;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(74, 115, 56, 0.3);
            }
            .btn-secondary {
                background: #fff;
                color: #525252;
                border: 1px solid #e5e5e5;
            }
            .btn-secondary:hover {
                background: #fafafa;
                border-color: #d4d4d4;
            }
        </style>
    </head>
    <body>
        <div class="error-container">
            <div class="error-code">404</div>
            <h1 class="error-title">Page Not Found</h1>
            <p class="error-message">The page you're looking for doesn't exist or has been moved.</p>
            <div class="error-actions">
                <a href="/dashboard" class="btn btn-primary">Go to Dashboard</a>
                <a href="/" class="btn btn-secondary">Home</a>
            </div>
        </div>
    </body>
    </html>
    """
    return error_html, 404

@app.errorhandler(500)
def internal_error(error):
    """500 error handler - professional error page"""
    db.session.rollback()
    log_security_event('500_error', f"Path: {request.path}, Error: {str(error)}", 'ERROR')
    
    # Return JSON for API requests, HTML for browser requests
    if request.path.startswith('/api/'):
        return jsonify({'error': 'An internal error occurred. Please try again later.'}), 500
    
    error_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Server Error - Employee Suite</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, #f5f5f5 0%, #fafafa 100%);
                color: #171717;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                padding: 24px;
            }
            .error-container {
                text-align: center;
                max-width: 500px;
            }
            .error-code {
                font-size: 120px;
                font-weight: 700;
                color: #dc2626;
                line-height: 1;
                margin-bottom: 16px;
            }
            .error-title {
                font-size: 28px;
                font-weight: 600;
                color: #0a0a0a;
                margin-bottom: 12px;
            }
            .error-message {
                font-size: 16px;
                color: #737373;
                margin-bottom: 32px;
                line-height: 1.6;
            }
            .error-actions {
                display: flex;
                gap: 12px;
                justify-content: center;
                flex-wrap: wrap;
            }
            .btn {
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 500;
                text-decoration: none;
                transition: all 0.2s;
                border: none;
                cursor: pointer;
            }
            .btn-primary {
                background: #4a7338;
                color: #fff;
            }
            .btn-primary:hover {
                background: #3a5c2a;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(74, 115, 56, 0.3);
            }
            .btn-secondary {
                background: #fff;
                color: #525252;
                border: 1px solid #e5e5e5;
            }
            .btn-secondary:hover {
                background: #fafafa;
                border-color: #d4d4d4;
            }
        </style>
    </head>
    <body>
        <div class="error-container">
            <div class="error-code">500</div>
            <h1 class="error-title">Server Error</h1>
            <p class="error-message">Something went wrong on our end. We've been notified and are working on a fix.</p>
            <div class="error-actions">
                <a href="/dashboard" class="btn btn-primary">Go to Dashboard</a>
                <a href="javascript:location.reload()" class="btn btn-secondary">Try Again</a>
            </div>
        </div>
    </body>
    </html>
    """
    return error_html, 500

@app.errorhandler(413)
def request_too_large(error):
    """413 error handler for oversized requests"""
    log_security_event('request_too_large', f"IP: {request.remote_addr}, Size: {request.content_length}", 'WARNING')
    return jsonify({'error': 'Request too large'}), 413

@app.errorhandler(429)
def rate_limit_exceeded(error):
    """429 error handler for rate limiting"""
    log_security_event('rate_limit_exceeded', f"IP: {request.remote_addr}, Path: {request.path}", 'WARNING')
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

# CSV Export Endpoints
@app.route('/api/export/inventory', methods=['GET'])
@login_required
@require_access
def export_inventory_csv():
    """Export inventory to CSV"""
    try:
        from flask import session, Response
        from inventory import check_inventory
        import csv
        import io
        
        # Get inventory data from session or regenerate
        inventory_data = session.get('inventory_data', [])
        
        if not inventory_data:
            # Regenerate if not in session
            result = check_inventory()
            if result.get('success') and 'inventory_data' in result:
                inventory_data = result['inventory_data']
                session['inventory_data'] = inventory_data
        
        if not inventory_data:
            return "No inventory data available. Please check inventory first.", 404
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Product', 'SKU', 'Stock', 'Price'])
        
        for item in inventory_data:
            writer.writerow([
                item.get('product', 'N/A'),
                item.get('sku', 'N/A'),
                item.get('stock', 0),
                item.get('price', 'N/A')
            ])
        
        # Return CSV file
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=inventory_{datetime.utcnow().strftime("%Y%m%d")}.csv'}
        )
        return response
        
    except Exception as e:
        logger.error(f"Error exporting inventory CSV: {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to export inventory: {str(e)}"}), 500

@app.route('/api/export/report', methods=['GET'])
@login_required
@require_access
def export_report_csv():
    """Export revenue report to CSV"""
    try:
        from flask import session, Response
        from reporting import generate_report
        import csv
        import io
        
        # Get report data from session or regenerate
        report_data = session.get('report_data', {})
        
        if not report_data:
            # Regenerate if not in session
            data = generate_report()
            if data.get('success') and 'report_data' in data:
                report_data = data['report_data']
        
        if not report_data or 'products' not in report_data:
            return "No report data available. Please generate report first.", 404
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Product', 'Revenue', 'Percentage', 'Total Revenue', 'Total Orders'])
        
        total_revenue = report_data.get('total_revenue', 0)
        total_orders = report_data.get('total_orders', 0)
        
        for product, revenue in report_data.get('products', [])[:10]:
            percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0
            writer.writerow([
                product,
                f"${revenue:,.2f}",
                f"{percentage:.1f}%",
                f"${total_revenue:,.2f}",
                total_orders
            ])
        
        # Return CSV file
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=revenue_report_{datetime.utcnow().strftime("%Y%m%d")}.csv'}
        )
        return response
        
    except Exception as e:
        logger.error(f"Error exporting report CSV for user {current_user.id}: {str(e)}", exc_info=True)
        return f"Error exporting CSV: {str(e)}", 500

# Initialize database tables on startup (safe for production - only creates if don't exist)
def init_db():
    """Initialize database tables - safe to run multiple times"""
    with app.app_context():
        try:
            db.create_all()
            # Add reset_token columns if they don't exist (migration)
            # SQLite-compatible: just try to add and catch errors
            try:
                logger.info("Checking for reset_token columns...")
                try:
                    db.session.execute(db.text("""
                        ALTER TABLE users 
                        ADD COLUMN reset_token VARCHAR(100)
                    """))
                    db.session.execute(db.text("""
                        ALTER TABLE users 
                        ADD COLUMN reset_token_expires TIMESTAMP
                    """))
                    db.session.commit()
                    logger.info("✅ reset_token columns added successfully")
                except Exception as alter_error:
                    error_str = str(alter_error).lower()
                    # Column might already exist (race condition or already added)
                    if "duplicate column" in error_str or "already exists" in error_str:
                        logger.info("✅ reset_token columns already exist")
                    else:
                        logger.warning(f"Could not add reset_token columns: {alter_error}")
                    db.session.rollback()
            except Exception as e:
                # If check fails, try to add columns anyway (might work)
                logger.warning(f"Could not check for reset_token columns: {e}")
            
            # Migrate shopify_stores table - add new columns
            # CRITICAL: Handle each column separately with proper transaction management
            try:
                from migrate_shopify_store_columns import migrate_shopify_store_columns
                migrate_shopify_store_columns(app, db)
            except Exception as e:
                logger.warning(f"Could not migrate shopify_stores columns via function: {e}")
                # Try manual migration as fallback (SQLite-compatible)
                logger.info("Adding shop_id, charge_id, uninstalled_at columns (fallback)...")
                columns = [
                    ("shop_id", "BIGINT"),
                    ("charge_id", "VARCHAR(255)"),
                    ("uninstalled_at", "TIMESTAMP")
                ]
                for col_name, col_type in columns:
                    # CRITICAL: Each column in separate transaction to prevent cascading failures
                    try:
                        # Check if column exists first (PostgreSQL-safe)
                        try:
                            result = db.session.execute(db.text(f"""
                                SELECT column_name 
                                FROM information_schema.columns 
                                WHERE table_name='shopify_stores' AND column_name='{col_name}'
                            """))
                            if result.fetchone():
                                logger.info(f"✅ {col_name} column already exists")
                                continue
                        except Exception as check_error:
                            # If check fails, try to add anyway
                            logger.debug(f"Could not check for {col_name}: {check_error}")
                        
                        # Add column in separate transaction
                        db.session.execute(db.text(f"""
                            ALTER TABLE shopify_stores 
                            ADD COLUMN {col_name} {col_type}
                        """))
                        db.session.commit()
                        logger.info(f"✅ {col_name} column added successfully")
                    except Exception as col_error:
                        # CRITICAL: Rollback immediately on error to prevent transaction abort
                        try:
                            db.session.rollback()
                        except Exception:
                            pass
                        
                        error_str = str(col_error).lower()
                        if "duplicate column" in error_str or "already exists" in error_str or "current transaction is aborted" in error_str:
                            logger.info(f"✅ {col_name} column already exists or transaction aborted (safe to ignore)")
                            # Force new transaction for next column
                            try:
                                db.session.rollback()
                            except Exception:
                                pass
                        else:
                            logger.warning(f"Could not add {col_name} column: {col_error}")
                            # Continue with next column even if this one failed
                            try:
                                db.session.rollback()
                            except Exception:
                                pass
            
            logger.info("Database tables initialized/verified")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")

# Lazy database initialization - don't block app startup
# CRITICAL: Render deployment timeout fix - don't initialize DB on import
_db_initialized = False

def ensure_db_initialized():
    """Lazy database initialization - called on first request"""
    global _db_initialized
    if _db_initialized:
        return
    try:
        init_db()
        _db_initialized = True
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization deferred: {e}")

try:
    import json
    shopify_routes = [str(rule) for rule in app.url_map.iter_rules() if 'shopify' in str(rule)]
    logger.info(f"App starting - Shopify routes: {len(shopify_routes)}, Total routes: {len(list(app.url_map.iter_rules()))}")
except Exception as e:
    logger.error(f"Failed to log startup info: {e}")
# #endregion

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    # Debug mode only in development (gunicorn overrides this in production)
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
