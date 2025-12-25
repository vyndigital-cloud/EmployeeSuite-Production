import sys
import os
import signal
import traceback
import logging

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

from flask import Flask, jsonify, render_template_string, redirect, url_for, request, session
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
    try:
        return User.query.get(int(user_id))
    except BaseException:
        # Catch segfault precursors - return None to let Flask-Login handle it
        try:
            db.session.rollback()
        except Exception:
            pass
        finally:
            try:
                db.session.remove()
            except Exception:
                pass
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
    # CRITICAL: Never use server-side redirect() - it causes iframe to load accounts.shopify.com
    # Instead, redirect to /install route which handles App Bridge redirect properly
    if embedded == '1' or (shop and host):
        if shop:
            install_url = url_for('oauth.install', shop=shop, host=host) if host else url_for('oauth.install', shop=shop)
            logger.info(f"Unauthorized embedded app request - redirecting to OAuth via install route: {install_url}")
            # Use client-side redirect by rendering HTML that loads the install route
            # The install route will handle App Bridge redirect properly
            from flask import render_template_string
            return render_template_string(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Redirecting...</title>
                <script>
                    window.location.href = '{install_url}';
                </script>
            </head>
            <body>
                <p>Redirecting...</p>
            </body>
            </html>
            """)
    
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
        # CRITICAL: Always remove session to prevent segfaults from stale connections
        try:
            db.session.remove()
        except Exception as e:
            # Non-critical - session might already be removed
            logger.debug(f"Session remove failed (non-critical): {e}")
        
        # CRITICAL: Disable garbage collection in teardown - it can cause segfaults
        # Let Python's automatic GC handle it instead
        # if error:
        #     import gc
        #     gc.collect()  # DISABLED - causes segfaults after response
    except BaseException as e:
        # Catch ALL exceptions including segfault precursors (SystemExit, KeyboardInterrupt, etc.)
        # CRITICAL: Never let teardown crash - response already sent
        try:
            try:
                db.session.rollback()
            except Exception:
                pass
            try:
                db.session.remove()
            except Exception:
                pass
        except Exception:
            # Even rollback/remove can fail - just log and continue
            pass
        # CRITICAL: Disable gc.collect() in teardown - causes segfaults
        # import gc
        # gc.collect()  # DISABLED - causes segfaults after response
        logger.debug(f"Teardown error handled (non-critical): {type(e).__name__}")
    # CRITICAL: Do NOT access request or response here
    # This function is called during app context teardown, which can happen outside requests
    # Request/response handling should be done in after_request handler instead

# Request validation before processing (optimized - fast checks only)
@app.before_request
def validate_request_security():
    """Validate incoming requests for security - minimal checks only"""
    # Skip validation for static files, health checks
    if request.endpoint in ('static', 'health') or request.endpoint is None:
        return
    
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
            
            // Add embedded class to body for CSS targeting
            if (window.isEmbedded) {
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
            script.async = false; // Load synchronously for reliability
            script.crossOrigin = 'anonymous'; // CORS for CDN
            
            // Initialize immediately when loaded
            script.onload = function() {
                console.log('✅ App Bridge script loaded successfully');
                try {
                    // Wait for App Bridge to be available (increased timeout for slower networks)
                    var attempts = 0;
                    var maxAttempts = 150; // 150 * 100ms = 15 seconds max
                    
                    function init() {
                        attempts++;
                        if (attempts % 10 === 0) {
                            console.log('🔄 App Bridge init attempt', attempts, 'of', maxAttempts);
                        }
                        
                        // Check multiple possible global names for App Bridge
                        var AppBridge = window['app-bridge'] || window['ShopifyAppBridge'] || window.appBridge;
                        
                        if (typeof AppBridge === 'undefined' || !AppBridge) {
                            if (attempts < maxAttempts) {
                                setTimeout(init, 100);
                                return;
                            }
                            console.error('❌ App Bridge not available after timeout');
                            console.error('Checked: window["app-bridge"], window["ShopifyAppBridge"], window.appBridge');
                            console.error('Script loaded:', script.src);
                            console.error('Script onload fired:', true);
                            var relevantKeys = Object.keys(window).filter(function(k) {
                                return k.toLowerCase().includes('app') || 
                                       k.toLowerCase().includes('bridge') || 
                                       k.toLowerCase().includes('shopify');
                            });
                            console.error('Available window properties:', relevantKeys);
                            window.shopifyApp = null;
                            window.appBridgeReady = true;
                            showAppBridgeError('App Bridge script loaded but object not found. This may be a CDN issue. Please refresh the page or contact support.');
                            return;
                        }
                        
                        console.log('✅ App Bridge object found:', typeof AppBridge);
                        
                        try {
                            // App Bridge v3 uses .default, older versions might use .create
                            var createApp = AppBridge.default || AppBridge.create || AppBridge;
                            if (typeof createApp !== 'function') {
                                console.error('❌ App Bridge createApp is not a function:', typeof createApp);
                                console.log('AppBridge object:', AppBridge);
                                if (attempts < maxAttempts) {
                                    setTimeout(init, 100);
                                    return;
                                }
                                window.shopifyApp = null;
                                window.appBridgeReady = true;
                                showAppBridgeError('App Bridge initialization failed: createApp not found. Please refresh the page.');
                                return;
                            }
                            // Get API key from template
                            var apiKey = '{{ SHOPIFY_API_KEY or "" }}';
                            console.log('🔑 API Key check:', apiKey ? 'Present (length: ' + apiKey.length + ')' : 'MISSING');
                            
                            // CRITICAL: If API key is missing, try to get from window (fallback)
                            if (!apiKey || apiKey === '' || apiKey.trim() === '') {
                                console.warn('⚠️ API key not found in template, checking window...');
                                apiKey = window.SHOPIFY_API_KEY || '';
                            }
                            
                            // CRITICAL: Both API key AND host are REQUIRED for embedded apps
                            if (!apiKey || apiKey === '' || apiKey.trim() === '') {
                                console.error('❌ SHOPIFY_API_KEY is missing - App Bridge cannot initialize');
                                console.error('🔍 Template value was:', '{{ SHOPIFY_API_KEY or "" }}'.substring(0, 20) + '...');
                                window.shopifyApp = null;
                                window.appBridgeReady = true;
                                showAppBridgeError('Configuration Error: SHOPIFY_API_KEY environment variable is not set. Please check your deployment configuration.');
                                return;
                            }
                            
                            console.log('✅ API Key found:', apiKey.substring(0, 8) + '...');
                            console.log('🔍 Host check:', host ? 'Present (' + host.substring(0, 30) + '...)' : 'MISSING');
                            
                            if (!host || host === '' || host.trim() === '') {
                                console.error('❌ Host parameter is missing - App Bridge cannot initialize');
                                console.error('🔍 URL params:', window.location.search);
                                window.shopifyApp = null;
                                window.appBridgeReady = true;
                                showAppBridgeError('Configuration Error: Missing host parameter. Make sure you are accessing the app from within Shopify admin. If the issue persists, please refresh the page.');
                                return;
                            }
                            
                            // Use host as-is (Shopify provides it correctly encoded)
                            if (apiKey && apiKey !== '' && apiKey.trim() !== '' && host && host !== '' && host.trim() !== '') {
                                try {
                                    console.log('🚀 Initializing App Bridge with:', {
                                        apiKeyLength: apiKey.length,
                                        hostLength: host.length,
                                        hasCreateApp: typeof createApp === 'function'
                                    });
                                    
                                    window.shopifyApp = createApp({
                                        apiKey: apiKey.trim(),
                                        host: host.trim() // Use original encoded host
                                    });
                                    
                                    console.log('✅ App Bridge initialized successfully!');
                                    console.log('✅ App object:', window.shopifyApp ? 'created' : 'failed');
                                    window.appBridgeReady = true;
                                    
                                    // Enable buttons now that App Bridge is ready
                                    enableEmbeddedButtons();
                                } catch (initError) {
                                    console.error('❌ App Bridge createApp error:', initError);
                                    console.error('Error details:', {
                                        name: initError.name,
                                        message: initError.message,
                                        stack: initError.stack
                                    });
                                    window.shopifyApp = null;
                                    window.appBridgeReady = true;
                                    showAppBridgeError('Initialization Error: ' + (initError.message || 'Unknown error') + '. Please refresh the page or contact support.');
                                }
                            } else {
                                console.error('❌ Validation failed:', {
                                    apiKey: apiKey ? ('present (' + apiKey.length + ' chars)'): 'missing',
                                    host: host ? ('present (' + host.length + ' chars)') : 'missing'
                                });
                                window.shopifyApp = null;
                                window.appBridgeReady = true;
                                showAppBridgeError('Configuration Error: Missing required parameters. API Key: ' + (apiKey ? 'OK' : 'MISSING') + ', Host: ' + (host ? 'OK' : 'MISSING') + '. Please check your deployment settings.');
                            }
                        } catch (e) {
                            console.error('❌ App Bridge init error:', e);
                            window.shopifyApp = null;
                            window.appBridgeReady = true;
                            showAppBridgeError('App Bridge error: ' + e.message);
                        }
                    }
                    
                    init();
                } catch (e) {
                    console.error('❌ App Bridge load error:', e);
                    window.shopifyApp = null;
                    window.appBridgeReady = true;
                    showAppBridgeError('Failed to load App Bridge: ' + e.message);
                }
            };
            
            script.onerror = function(error) {
                console.error('❌ Failed to load App Bridge script from CDN');
                console.error('Error details:', error);
                console.error('Script URL:', script.src);
                
                // Try alternative CDN URL
                console.log('🔄 Trying alternative CDN URL...');
                var fallbackScript = document.createElement('script');
                fallbackScript.src = 'https://cdn.shopify.com/shopifycloud/app-bridge.js';
                fallbackScript.async = false;
                fallbackScript.crossOrigin = 'anonymous';
                fallbackScript.onload = function() {
                    console.log('✅ App Bridge loaded from fallback URL');
                    // Retry initialization after a brief delay
                    setTimeout(function() {
                        if (typeof window['app-bridge'] !== 'undefined') {
                            try {
                                var AppBridge = window['app-bridge'];
                                var createApp = AppBridge.default || AppBridge.create || AppBridge;
                                var apiKey = '{{ SHOPIFY_API_KEY or "" }}'.trim();
                                
                                if (apiKey && host) {
                                    window.shopifyApp = createApp({
                                        apiKey: apiKey,
                                        host: host
                                    });
                                    window.appBridgeReady = true;
                                    console.log('✅ App Bridge initialized from fallback');
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
                            console.error('❌ App Bridge not available even after fallback load');
                            window.shopifyApp = null;
                            window.appBridgeReady = true;
                            showAppBridgeError('Failed to load App Bridge. Please check your internet connection and refresh the page.');
                        }
                    }, 200);
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
        // Defer analytics loading
        window.addEventListener('load', function() {
            var script = document.createElement('script');
            script.async = true;
            script.src = 'https://www.googletagmanager.com/gtag/js?id=G-RBBQ4X7FJ3';
            document.head.appendChild(script);
            
            script.onload = function() {
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', 'G-RBBQ4X7FJ3');
            };
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
                <a href="/settings/shopify" class="nav-btn">Settings</a>
                <a href="{{ url_for('billing.subscribe') }}" class="nav-btn nav-btn-primary">Subscribe</a>
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
            <a href="{{ url_for('billing.subscribe') }}" class="banner-action">Subscribe Now</a>
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
                <button class="card-btn" onclick="processOrders(this)" aria-label="View pending orders">
                    <span>View Orders</span>
                    <span style="font-size: 12px; opacity: 0.8;">→</span>
                </button>
                {% else %}
                <button class="card-btn" onclick="showSubscribePrompt()" style="opacity: 0.6; cursor: not-allowed;" disabled aria-label="Subscribe to view orders">
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
                <button class="card-btn" onclick="updateInventory(this)" aria-label="Check inventory levels">
                    <span>Check Inventory</span>
                    <span style="font-size: 12px; opacity: 0.8;">→</span>
                </button>
                {% else %}
                <button class="card-btn" onclick="showSubscribePrompt()" style="opacity: 0.6; cursor: not-allowed;" disabled aria-label="Subscribe to check inventory">
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
                <button class="card-btn" onclick="generateReport(this)" aria-label="Generate revenue report">
                    <span>Generate Report</span>
                    <span style="font-size: 12px; opacity: 0.8;">→</span>
                </button>
                {% else %}
                <button class="card-btn" onclick="showSubscribePrompt()" style="opacity: 0.6; cursor: not-allowed;" disabled aria-label="Subscribe to generate reports">
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
                    <a href="{{ url_for('billing.subscribe') }}" style="display: inline-block; background: #0a0a0a; color: #fff; padding: 14px 28px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 15px; transition: all 0.2s;">Subscribe Now →</a>
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
            
            // CRITICAL: Wait for App Bridge to be ready before making requests
            if (isEmbedded && !window.appBridgeReady) {
                setButtonLoading(button, false);
                document.getElementById('output').innerHTML = `
                    <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                        <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ Initializing App...</div>
                        <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">Please wait while the app initializes. This should only take a moment.</div>
                        <button onclick="setTimeout(function(){processOrders(this);}, 500)" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                    </div>
                `;
                return;
            }
            
            if (isEmbedded && window.shopifyApp && window.appBridgeReady) {
                // In embedded mode, we MUST have session token - retry up to 3 times
                var retryCount = 0;
                var maxRetries = 3;
                
                function getTokenWithRetry() {
                    return window.shopifyApp.getSessionToken().then(function(token) {
                        if (!token && retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve, reject) {
                                setTimeout(function() {
                                    getTokenWithRetry().then(resolve).catch(reject);
                                }, 300);
                            });
                        }
                        return token;
                    }).catch(function(err) {
                        // If error and haven't exceeded retries, retry
                        if (retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve, reject) {
                                setTimeout(function() {
                                    getTokenWithRetry().then(resolve).catch(reject);
                                }, 300);
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
                    console.log('✅ Got session token, making API request...');
                    return fetch('/api/process_orders', {
                        headers: {'Authorization': 'Bearer ' + token},
                        signal: controller.signal
                    });
                }).catch(function(err) {
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
                // Not embedded - use regular fetch (Flask-Login handles auth)
                fetchPromise = fetch('/api/process_orders', {
                    signal: controller.signal
                });
            }
            
            fetchPromise
                .then(r => {
                    // Check if request was cancelled
                    if (controller.signal.aborted) {
                        return null;
                    }
                    if (!r.ok) {
                        return r.json().then(function(err) {
                            throw new Error(err.error || 'Network error');
                        });
                    }
                    return r.json();
                })
                .then(d => {
                    // Check if request was cancelled
                    if (!d) return;
                    
                    setButtonLoading(button, false);
                    activeRequests.processOrders = null;
                    debounceTimers.processOrders = null;
                    
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
                    setButtonLoading(button, false);
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
        }
        
        function updateInventory(button) {
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
            
            // CRITICAL: Wait for App Bridge to be ready before making requests
            if (isEmbedded && !window.appBridgeReady) {
                setButtonLoading(button, false);
                document.getElementById('output').innerHTML = `
                    <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                        <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ Initializing App...</div>
                        <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">Please wait while the app initializes. This should only take a moment.</div>
                        <button onclick="setTimeout(function(){updateInventory(this);}, 500)" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                    </div>
                `;
                return;
            }
            
            if (isEmbedded && window.shopifyApp && window.appBridgeReady) {
                // In embedded mode, we MUST have session token - retry up to 3 times
                var retryCount = 0;
                var maxRetries = 3;
                
                function getTokenWithRetry() {
                    return window.shopifyApp.getSessionToken().then(function(token) {
                        if (!token && retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve, reject) {
                                setTimeout(function() {
                                    getTokenWithRetry().then(resolve).catch(reject);
                                }, 300);
                            });
                        }
                        return token;
                }).catch(function(err) {
                        // If error and haven't exceeded retries, retry
                        if (retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve, reject) {
                                setTimeout(function() {
                                    getTokenWithRetry().then(resolve).catch(reject);
                                }, 300);
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
                    return fetch('/api/update_inventory', {
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
                fetchPromise = fetch('/api/update_inventory', {
                    signal: controller.signal
                });
            }
            
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
                                throw new Error(json.error || 'Request failed');
                            } catch (e) {
                                if (e.message) throw e;
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
                    debounceTimers.updateInventory = null;
                    
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
                    debounceTimers.updateInventory = null;
                    
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
        }
        
        function generateReport(button) {
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
            
            // CRITICAL: Wait for App Bridge to be ready before making requests
            if (isEmbedded && !window.appBridgeReady) {
                setButtonLoading(button, false);
                document.getElementById('output').innerHTML = `
                    <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                        <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ Initializing App...</div>
                        <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">Please wait while the app initializes. This should only take a moment.</div>
                        <button onclick="setTimeout(function(){generateReport(this);}, 500)" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                    </div>
                `;
                return;
            }
            
            if (isEmbedded && window.shopifyApp && window.appBridgeReady) {
                // In embedded mode, we MUST have session token - retry up to 3 times
                var retryCount = 0;
                var maxRetries = 3;
                
                function getTokenWithRetry() {
                    return window.shopifyApp.getSessionToken().then(function(token) {
                        if (!token && retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve, reject) {
                                setTimeout(function() {
                                    getTokenWithRetry().then(resolve).catch(reject);
                                }, 300);
                            });
                        }
                        return token;
                }).catch(function(err) {
                        // If error and haven't exceeded retries, retry
                        if (retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve, reject) {
                                setTimeout(function() {
                                    getTokenWithRetry().then(resolve).catch(reject);
                                }, 300);
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
                    const reportUrl = shopUrl ? `/api/generate_report?shop=${encodeURIComponent(shopUrl)}` : '/api/generate_report';
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
                // Get shop from URL or use current shop
                const shopUrl = new URLSearchParams(window.location.search).get('shop') || '';
                const reportUrl = shopUrl ? `/api/generate_report?shop=${encodeURIComponent(shopUrl)}` : '/api/generate_report';
                fetchPromise = fetch(reportUrl, {
                    signal: controller.signal
                });
            }
            
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
                    debounceTimers.generateReport = null;
                    
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
                    debounceTimers.generateReport = null;
                    
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
        }
        
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

@app.route('/')
def home():
    """Home page - SIMPLIFIED: Always render dashboard for embedded apps"""
    # Check if this is an embedded app request from Shopify
    shop = request.args.get('shop')
    embedded = request.args.get('embedded')
    host = request.args.get('host')
    
    # Check Referer header as Shopify sends requests from admin.shopify.com
    referer = request.headers.get('Referer', '')
    is_from_shopify_admin = 'admin.shopify.com' in referer
    
    # CRITICAL: For embedded apps, ALWAYS render dashboard - NEVER redirect
    # Redirects break iframes. Just render the dashboard HTML.
    is_embedded = embedded == '1' or shop or host or is_from_shopify_admin
    
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
                    try:
                        db.session.remove()
                    except Exception:
                        pass
                store = None
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
                        try:
                            db.session.remove()
                        except Exception:
                            pass
                    store = None
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
                        try:
                            db.session.remove()
                        except Exception:
                            pass
                    store = None
                if store and hasattr(store, 'shop_url') and store.shop_url:
                    shop_domain = store.shop_url
            
            # CRITICAL: Pass host parameter to template for App Bridge initialization
            host_param = request.args.get('host', '')
            
            return render_template_string(DASHBOARD_HTML, 
                                         trial_active=trial_active, 
                                         days_left=days_left, 
                                         is_subscribed=is_subscribed, 
                                         has_shopify=has_shopify, 
                                         has_access=has_access,
                                         quick_stats=quick_stats,
                                         shop_domain=shop_domain,
                                         SHOPIFY_API_KEY=os.getenv('SHOPIFY_API_KEY', ''),
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
            
            return render_template_string(DASHBOARD_HTML, 
                                         trial_active=trial_active, 
                                         days_left=days_left, 
                                         is_subscribed=is_subscribed, 
                                         has_shopify=has_shopify, 
                                         has_access=has_access,
                                         quick_stats=quick_stats,
                                         shop_domain=shop_domain,
                                         SHOPIFY_API_KEY=os.getenv('SHOPIFY_API_KEY', ''),
                                         host=host_param)
    
    # Regular (non-embedded) request handling
    if current_user.is_authenticated:
        # If user is authenticated, always go to dashboard (even if embedded params missing)
        return redirect(url_for('dashboard'))
    
    # Check if this might be an embedded request that lost its params
    # If referer is from Shopify admin, treat as embedded
    if is_from_shopify_admin:
        # Render dashboard for embedded apps even without explicit params
        # render_template_string is already imported at top of file
        # CRITICAL: Pass host parameter to template for App Bridge initialization
        host_param = request.args.get('host', '')
        
        return render_template_string(DASHBOARD_HTML, 
                                     trial_active=False, 
                                     days_left=0, 
                                     is_subscribed=False, 
                                     has_shopify=False, 
                                     has_access=False,
                                     quick_stats={'has_data': False, 'pending_orders': 0, 'total_products': 0, 'low_stock_items': 0},
                                     shop_domain=shop or '',
                                     SHOPIFY_API_KEY=os.getenv('SHOPIFY_API_KEY', ''),
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
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            if 'myshopify.com' in parsed.netloc:
                shop = parsed.netloc.split('.')[0] + '.myshopify.com'
            elif '/store/' in parsed.path:
                shop_name = parsed.path.split('/store/')[1].split('/')[0]
                shop = f"{shop_name}.myshopify.com"
        except Exception:
            pass
    
    # CRITICAL: For embedded apps without shop, redirect to OAuth immediately
    if is_embedded and not shop:
        logger.warning(f"Embedded app request but no shop param found - redirecting to install")
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
    # For regular requests, require login
    if not is_embedded and not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
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
                
                // Fallback: use window.top.location.href if App Bridge not available
                if (attempts < maxAttempts) {{
                    setTimeout(redirectToOAuth, 100);
                }                }} else {{
                    console.warn('⚠️ App Bridge not available, showing button with target="_top"');
                    // CRITICAL: Never use programmatic redirects - show button with target="_top" instead
                    // This prevents "accounts.shopify.com refused to connect" error
                    document.body.innerHTML = `
                        <div style="padding: 40px; text-align: center; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #fff; border-radius: 8px; max-width: 500px; margin: 40px auto; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                            <h2 style="color: #202223; margin-bottom: 16px; font-size: 20px;">Connect Your Shopify Store</h2>
                            <p style="color: #6d7175; margin-bottom: 24px; line-height: 1.5;">Click the button below to authorize the connection. This will open in the top-level window.</p>
                            <a href="${installUrl}" target="_top" style="display: inline-block; background: #008060; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px; transition: background 0.2s;">Continue to Shopify Authorization →</a>
                        </div>
                    `;
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
    
    # Check if user has connected Shopify
    from models import ShopifyStore
    if user_authenticated:
        # DO NOT call db.session.remove() before query - let pool_pre_ping handle validation
        try:
            has_shopify = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first() is not None
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
    else:
        # For embedded apps without auth, check by shop param
        has_shopify = False
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
                    try:
                        db.session.remove()
                    except Exception:
                        pass
                store = None
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
                store = None
            if store:
                has_shopify = True
        is_subscribed = False
    
    # Skip slow API calls on dashboard load - just show empty stats
    # This prevents the page from hanging while waiting for Shopify API
    # Users can click buttons to load data when they need it
    quick_stats = {'has_data': False, 'pending_orders': 0, 'total_products': 0, 'low_stock_items': 0}
    
    # Store shop in session for API calls (if shop parameter is present)
    if shop:
        from flask import session
        session['current_shop'] = shop
        session.permanent = True
        logger.info(f"Stored shop in session: {shop} for user {current_user.id if user_authenticated else 'anonymous'}")
    
    # Get shop domain and API key for App Bridge initialization
    shop_domain = shop or ''
    if user_authenticated and has_shopify:
        try:
            db.session.remove()
            store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
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
            store = None
        if store:
            shop_domain = store.shop_url
            # Also store in session if not already set
            if shop_domain and not shop:
                from flask import session
                session['current_shop'] = shop_domain
                session.permanent = True
    elif shop and has_shopify:
        store = None
        # DO NOT call db.session.remove() before query - let pool_pre_ping handle validation
        try:
            store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
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
            store = None
        if store and hasattr(store, 'shop_url') and store.shop_url:
            shop_domain = store.shop_url
    
    # CRITICAL: Pass host parameter to template for App Bridge initialization
    host_param = request.args.get('host', '')
    
    return render_template_string(DASHBOARD_HTML, 
                                 trial_active=trial_active, 
                                 days_left=days_left, 
                                 is_subscribed=is_subscribed, 
                                 has_shopify=has_shopify, 
                                 has_access=has_access,
                                 quick_stats=quick_stats,
                                 shop_domain=shop_domain,
                                 SHOPIFY_API_KEY=os.getenv('SHOPIFY_API_KEY', ''),
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
    # Get authenticated user (supports both Flask-Login and session tokens)
    user, error_response = get_authenticated_user()
    if error_response:
        return error_response
    
    # Check access
    if not user.has_access():
        return jsonify({
            'error': 'Subscription required',
            'success': False,
            'action': 'subscribe',
            'message': 'Your trial has ended. Subscribe to continue using Employee Suite.',
            'subscribe_url': url_for('billing.subscribe')
        }), 403
    
    # Store user ID before login_user to avoid recursion issues
    user_id = user.id if hasattr(user, 'id') else getattr(user, 'id', None)
    
    # Temporarily set current_user for process_orders() function
    # (it expects current_user to be set)
    from flask_login import login_user
    login_user(user, remember=False)
    
    try:
        result = process_orders()
        if isinstance(result, dict):
            return jsonify(result)
        else:
            return jsonify({"message": str(result), "success": True})
    except MemoryError:
        logger.error(f"Memory error processing orders for user {user_id} - clearing cache")
        from performance import clear_cache as clear_perf_cache
        clear_perf_cache()
        return jsonify({"error": "Memory error - please try again", "success": False}), 500
    except SystemExit:
        # Re-raise system exits (like from sys.exit())
        raise
    except BaseException as e:
        # Catch all other exceptions including segmentation faults precursors
        logger.error(f"Critical error processing orders for user {user_id}: {type(e).__name__}: {str(e)}", exc_info=True)
        from performance import clear_cache as clear_perf_cache
        try:
            clear_perf_cache()
        except Exception:
            pass
        return jsonify({"error": "An unexpected error occurred. Please try again or contact support if this persists.", "success": False}), 500

@app.route('/api/update_inventory', methods=['GET', 'POST'])
def api_update_inventory():
    # Get authenticated user (supports both Flask-Login and session tokens)
    user, error_response = get_authenticated_user()
    if error_response:
        return error_response
    
    if not user.has_access():
        return jsonify({
            'error': 'Subscription required',
            'success': False,
            'action': 'subscribe',
            'message': 'Your trial has ended. Subscribe to continue using Employee Suite.',
            'subscribe_url': url_for('billing.subscribe')
        }), 403
    
    # Store user ID before login_user to avoid recursion issues
    user_id = user.id if hasattr(user, 'id') else getattr(user, 'id', None)
    
    # Set current_user for update_inventory() function
    from flask_login import login_user
    login_user(user, remember=False)
    
    try:
        # Import at function level to avoid UnboundLocalError
        from performance import clear_cache as clear_perf_cache
        clear_perf_cache('get_products')
        result = update_inventory()
        if isinstance(result, dict):
            # Store inventory data in session for CSV export
            if result.get('success') and 'inventory_data' in result:
                from flask import session
                session['inventory_data'] = result['inventory_data']
            return jsonify(result)
        else:
            return jsonify({"success": False, "error": str(result)})
    except MemoryError:
        logger.error(f"Memory error updating inventory for user {user_id} - clearing cache")
        from performance import clear_cache as clear_perf_cache
        clear_perf_cache()
        return jsonify({"success": False, "error": "Memory error - please try again"}), 500
    except SystemExit:
        # Re-raise system exits (like from sys.exit())
        raise
    except BaseException as e:
        # Catch all other exceptions including segmentation faults precursors
        logger.error(f"Critical error updating inventory for user {user_id}: {type(e).__name__}: {str(e)}", exc_info=True)
        from performance import clear_cache as clear_perf_cache
        try:
            clear_perf_cache()
        except Exception:
            pass
        return jsonify({"success": False, "error": "An unexpected error occurred. Please try again or contact support if this persists."}), 500

@app.route('/api/generate_report', methods=['GET', 'POST'])
def api_generate_report():
    """Generate revenue report with detailed crash logging"""
    user_id = None
    try:
        logging.info("=== REPORT GENERATION START ===")
        logging.info(f"Request method: {request.method}")
        logging.info(f"Request path: {request.path}")
        logging.info(f"Request headers: {dict(request.headers)}")
        
        # Get authenticated user (supports both Flask-Login and session tokens)
        logging.info("Step 1: Getting authenticated user...")
        user, error_response = get_authenticated_user()
        if error_response:
            logging.warning("Step 1 FAILED: Authentication error")
            return error_response
        
        logging.info(f"Step 1 SUCCESS: User authenticated: {user.email if hasattr(user, 'email') else 'N/A'}")
        
        # Store user ID before login_user to avoid recursion issues
        user_id = user.id if hasattr(user, 'id') else getattr(user, 'id', None)
        logging.info(f"Step 2: User ID extracted: {user_id}")
        
        if not user.has_access():
            logging.warning(f"Step 2 FAILED: User {user_id} does not have access")
            return jsonify({
                'error': 'Subscription required',
                'success': False,
                'action': 'subscribe',
                'message': 'Your trial has ended. Subscribe to continue using Employee Suite.',
                'subscribe_url': url_for('billing.subscribe')
            }), 403
        
        logging.info(f"Step 2 SUCCESS: User {user_id} has access")
        
        # Set current_user for generate_report() function
        logging.info("Step 3: Logging in user...")
        from flask_login import login_user
        login_user(user, remember=False)
        logging.info("Step 3 SUCCESS: User logged in")
        
        logger.info(f"Generate report called by user {user_id}")
        logging.info(f"Step 4: Calling generate_report() for user {user_id}...")
        
        # Get shop_url from request args, session, or None (will use first active store)
        from flask import session
        shop_url = request.args.get('shop') or session.get('current_shop') or None
        if shop_url:
            logging.info(f"Step 4: Using shop_url from request/session: {shop_url}")
        else:
            logging.info(f"Step 4: No shop_url in request/session, will use first active store for user")
        
        # CRITICAL: DO NOT call db.session.remove() here - let SQLAlchemy manage connections
        # Removing sessions before queries can cause segfaults by corrupting connection state
        from reporting import generate_report
        # Pass user_id and shop_url to avoid recursion and ensure correct store
        logging.info("Step 4a: Imported generate_report function")
        logging.info("Step 4b: Calling generate_report(user_id={}, shop_url={})...".format(user_id, shop_url))
        
        data = generate_report(user_id=user_id, shop_url=shop_url)
        
        logging.info(f"Step 4 SUCCESS: generate_report() returned, checking results...")
        logging.info(f"Step 4 result keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        
        if data.get('error') and data['error'] is not None:
            error_msg = data['error']
            logging.warning(f"Step 4 ERROR: Report generation returned error: {error_msg[:200]}")
            if 'No Shopify store connected' in error_msg:
                logger.info(f"Generate report: No store connected for user {user_id}")
            else:
                logger.error(f"Generate report error for user {user_id}: {error_msg}")
            return error_msg, 500
        
        if not data.get('message'):
            logging.warning(f"Step 4 WARNING: No message in report data")
            logger.warning(f"Generate report returned no message for user {user_id}")
            return '<h3 class="error">❌ No report data available</h3>', 500
        
        html = data.get('message', '<h3 class="error">❌ No report data available</h3>')
        logging.info(f"Step 5: Report HTML generated, length: {len(html)} characters")
        
        from flask import session
        if 'report_data' in data:
            session['report_data'] = data['report_data']
            logging.info("Step 5a: Report data stored in session")
        
        logging.info("=== REPORT GENERATION SUCCESS ===")
        return html, 200
        
    except MemoryError as e:
        logging.error("=== CRASH DETECTED ===")
        logging.error(f"Error type: {type(e).__name__}")
        logging.error(f"Error message: {str(e)}")
        logging.error(f"Full traceback:\n{traceback.format_exc()}")
        logging.error("=== END CRASH LOG ===")
        logger.error(f"Memory error generating report for user {user_id} - clearing cache")
        from performance import clear_cache as clear_perf_cache
        clear_perf_cache()
        return jsonify({"success": False, "error": "Memory error - please try again"}), 500
    except SystemExit as e:
        logging.error("=== CRASH DETECTED ===")
        logging.error(f"Error type: {type(e).__name__}")
        logging.error(f"Error message: {str(e)}")
        logging.error(f"Full traceback:\n{traceback.format_exc()}")
        logging.error("=== END CRASH LOG ===")
        # Re-raise system exits (like from sys.exit())
        raise
    except BaseException as e:
        logging.error("=== CRASH DETECTED ===")
        logging.error(f"Error type: {type(e).__name__}")
        logging.error(f"Error message: {str(e)}")
        logging.error(f"Full traceback:\n{traceback.format_exc()}")
        logging.error(f"User ID: {user_id}")
        logging.error(f"Exception args: {e.args}")
        logging.error("=== END CRASH LOG ===")
        # Catch all other exceptions including segmentation faults precursors
        logger.error(f"Critical error generating report for user {user_id}: {type(e).__name__}: {str(e)}", exc_info=True)
        from performance import clear_cache as clear_perf_cache
        try:
            clear_perf_cache()
        except Exception:
            pass
        return jsonify({"success": False, "error": "An unexpected error occurred. Please try again or contact support if this persists."}), 500
    except Exception as e:
        logging.error("=== CRASH DETECTED ===")
        logging.error(f"Error type: {type(e).__name__}")
        logging.error(f"Error message: {str(e)}")
        logging.error(f"Full traceback:\n{traceback.format_exc()}")
        logging.error(f"User ID: {user_id}")
        logging.error("=== END CRASH LOG ===")
        logger.error(f"Error generating report for user {user_id}: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": f"Failed to generate report: {str(e)}"}), 500

@app.errorhandler(404)
def not_found(error):
    """404 error handler - professional error page"""
    log_security_event('404_error', f"Path: {request.path}", 'INFO')
    
    # Return JSON for API requests, HTML for browser requests
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    
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

# Run on import (for Render/Gunicorn)
init_db()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    # Debug mode only in development (gunicorn overrides this in production)
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
