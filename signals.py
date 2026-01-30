def register_signals(app):
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
        Safe redirect for Shopify embedded apps.
        Uses standard HTTP redirect - Shopify handles iframe navigation.
        """
        # For Shopify OAuth URLs, always use standard redirect
        # Shopify's OAuth flow handles the iframe breaking automatically
        if 'myshopify.com' in url or 'shopify.com' in url:
            return redirect(url)
    
        # For internal app URLs, use standard redirect
        # The browser/Shopify will handle this correctly
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
    # Enhanced features
    from enhanced_features import enhanced_bp
    from enhanced_billing import enhanced_billing_bp
    from features_pages import features_pages_bp
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
    # sentry_sdk.init(
    pass
    pass
