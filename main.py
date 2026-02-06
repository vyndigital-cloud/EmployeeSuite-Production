#!/usr/bin/env python3
"""
Production Main Entry Point - Bulletproof (Verified)
"""

import os
import sys
import logging
import json
from pathlib import Path
from datetime import datetime

# Add project directory to path
project_dir = Path(__file__).parent.absolute()
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# Configure logging for production speed
import traceback

# Initialize logger for this module first
logger = logging.getLogger(__name__)

# Import error logging with fallback
try:
    from error_logging import error_logger, log_errors
    logger.info("Error logging imported successfully")
except ImportError as e:
    logger.error(f"Error logging import failed: {e}")
    # Create a fallback error logger

# Import session token verification
try:
    from session_token_verification import verify_session_token
    logger.info("Session token verification imported successfully")
except ImportError as e:
    logger.error(f"Session token verification import failed: {e}")
    # Create a fallback decorator
    def verify_session_token(func):
        return func

# Create a fallback error logger
try:
    # Check if error_logger was imported successfully
    error_logger
except NameError:
    class FallbackErrorLogger:
        def __init__(self):
            self.errors = []
        
        def log_error(self, error, error_type="GENERAL", additional_context=None):
            error_entry = {
                'timestamp': datetime.now().isoformat(),
                'error': str(error),
                'type': error_type,
                'context': additional_context
            }
            self.errors.append(error_entry)
            logger.error(f"[{error_type}] {str(error)}")
            
        def log_user_action(self, action, user_id=None, details=None):
            logger.info(f"User Action: {action}")
            
        def log_system_event(self, event, details=None):
            logger.info(f"System Event: {event}")
            
        def get_recent_errors(self, count=50):
            return self.errors[-count:] if self.errors else []
    
    error_logger = FallbackErrorLogger()
    
    def log_errors(error_type="GENERAL"):
        def decorator(func):
            return func
        return decorator

# Optimized logging for production
logging.basicConfig(
    level=logging.INFO,  # INFO level for production monitoring
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info("Starting main.py - logging configured")

# Check critical imports
try:
    import flask
    logger.info(f"Flask version: {flask.__version__}")
except ImportError as e:
    logger.error(f"Flask import failed: {e}")
    sys.exit(1)

try:
    from models import db
    logger.info("Models imported successfully")
except ImportError as e:
    logger.error(f"Models import failed: {e}")

try:
    from extensions import db as ext_db
    logger.info("Extensions imported successfully")
except ImportError as e:
    logger.error(f"Extensions import failed: {e}")

# Set production defaults
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

# Add environment validation
required_env_vars = ['SHOPIFY_API_KEY', 'SHOPIFY_API_SECRET', 'SECRET_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.warning(f"Missing environment variables: {missing_vars}")
    logger.warning("App may not function properly without these variables")


# Create the app with better error handling
app = None
startup_error_details = None
factory_error_details = None

try:
    logger.info("Attempting to create app via app_factory.create_app()")
    from app_factory import create_app
    app = create_app()
    logger.info("App created successfully via app_factory")
    
    # Log successful startup
    error_logger.log_system_event("APP_STARTUP_SUCCESS", {
        'method': 'app_factory.create_app',
        'environment': os.getenv('ENVIRONMENT', 'unknown')
    })
        
except Exception as startup_error:
    startup_error_details = str(startup_error)
    logger.error(f"App factory failed with error: {startup_error}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    error_logger.log_error(startup_error, "STARTUP_ERROR")

    # Try startup.py as backup
    try:
        logger.info("Trying startup.create_app() as backup")
        from startup import create_app as startup_create_app
        app = startup_create_app()
        logger.info("App created successfully via startup.py")
        error_logger.log_system_event("APP_STARTUP_FALLBACK", {
            'method': 'startup.create_app'
        })
    except Exception as factory_error:
        factory_error_details = str(factory_error)
        logger.error(f"Startup factory also failed: {factory_error}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        error_logger.log_error(factory_error, "FACTORY_ERROR")

        # Ultimate fallback with detailed error info
        logger.info("Using ultimate fallback Flask app")
        from flask import Flask, jsonify
        app = Flask(__name__)
        
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key')
        
        error_logger.log_system_event("APP_STARTUP_ULTIMATE_FALLBACK")
        
        @app.route("/")
        def home():
            return jsonify({
                "status": "fallback app running", 
                "error": "main app failed to start",
                "startup_error": startup_error_details,
                "factory_error": factory_error_details
            })

        @app.route("/health")
        def health():
            return jsonify({
                "status": "fallback healthy",
                "errors": {
                    "startup_error": startup_error_details,
                    "factory_error": factory_error_details
                }
            })

        @app.route("/ready")
        def ready():
            return jsonify({"status": "ready", "timestamp": datetime.now().isoformat()})

# Only add the enhanced error handlers and routes if we have a successful app
if app and startup_error_details is None:
    # Register other blueprints after OAuth
    try:
        from auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
        logger.info("✅ Auth blueprint registered successfully")
    except ImportError as e:
        logger.error(f"Could not register auth blueprint: {e}")

    try:
        from shopify_routes import shopify_bp
        app.register_blueprint(shopify_bp)
        logger.info("✅ Shopify blueprint registered successfully")
    except ImportError as e:
        logger.error(f"Could not register shopify blueprint: {e}")

    # Register centralized error handlers
    try:
        from error_handlers import register_errors
        register_errors(app)
        logger.info("Error handlers registered successfully")
    except ImportError as e:
        logger.warning(f"Could not register error handlers: {e}")

    # Debug route to verify OAuth routes are registered
    @app.route('/debug/routes')
    def debug_routes():
        """Debug route to see all registered routes"""
        from flask import jsonify
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'rule': str(rule)
            })
        return jsonify(routes)

    # Redirect /admin to actual admin panel (override Render's scaling endpoint)
    @app.route('/admin')
    @app.route('/admin/')
    def redirect_admin():
        """Redirect /admin to /system-admin/login"""
        from flask import redirect
        return redirect('/system-admin/login', code=302)
    
    # Log all requests
    @app.before_request
    def log_request():
        """Log all incoming requests"""
        from flask import request, session
        error_logger.log_user_action(
            f"{request.method} {request.endpoint or request.path}",
            session.get('user_id') if session else None,
            {
                'shop_domain': request.headers.get('X-Shopify-Shop-Domain'),
                'user_agent': request.headers.get('User-Agent', '')[:100]
            }
        )

    # Error dashboard route
    @app.route('/system/errors')
    @log_errors("ADMIN_ERROR")
    def view_errors():
        """Admin route to view recent errors"""
        from flask import session, jsonify
        try:
            # Simple authentication check
            if not session.get('user_id'):
                return jsonify({'error': 'Unauthorized'}), 401
                
            recent_errors = error_logger.get_recent_errors(100)
            
            return jsonify({
                'total_errors': len(recent_errors),
                'errors': recent_errors[-20:],  # Last 20 errors
                'status': 'success'
            })
            
        except Exception as e:
            error_logger.log_error(e, "ADMIN_DASHBOARD_ERROR")
            return jsonify({'error': 'Failed to retrieve errors'}), 500

    # Performance dashboard route
    @app.route('/system/performance')
    @log_errors("ADMIN_PERFORMANCE")
    def view_performance():
        """Admin route to view performance metrics"""
        from flask import session, jsonify, render_template_string, request
        try:
            # Simple authentication check
            if not session.get('user_id'):
                return jsonify({'error': 'Unauthorized'}), 401
            
            # Get cache efficiency data
            try:
                from performance import get_cache_efficiency
                cache_data = get_cache_efficiency()
            except ImportError:
                cache_data = {
                    "cache_efficiency": {
                        "cache_size": 0,
                        "hit_rate": 0,
                        "memory_usage_mb": 0.0,
                        "total_hits": 0,
                        "total_requests": 0
                    },
                    "current_tier": "standard",
                    "max_load_seen": 0.0,
                    "scaling_thresholds": {},
                    "status": "healthy"
                }
            
            # Check if request wants JSON
            if request.headers.get('Content-Type') == 'application/json' or request.args.get('format') == 'json':
                return jsonify(cache_data)
            
            # Return HTML dashboard
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Performance Dashboard</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 20px; background: #f6f6f7; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                    .metric { display: inline-block; margin: 10px 20px 10px 0; }
                    .metric-value { font-size: 24px; font-weight: bold; color: #008060; }
                    .metric-label { font-size: 14px; color: #6d7175; }
                    .status-healthy { color: #008060; }
                    .status-warning { color: #ff8c00; }
                    .status-error { color: #d72c0d; }
                    .refresh-btn { background: #008060; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Performance Dashboard</h1>
                    
                    <div class="card">
                        <h2>System Status: <span class="status-{{ status_class }}">{{ status|upper }}</span></h2>
                        <button class="refresh-btn" onclick="location.reload()">Refresh</button>
                    </div>
                    
                    <div class="card">
                        <h3>Cache Performance</h3>
                        <div class="metric">
                            <div class="metric-value">{{ hit_rate }}%</div>
                            <div class="metric-label">Hit Rate</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{{ cache_size }}</div>
                            <div class="metric-label">Cache Size</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{{ memory_usage }}MB</div>
                            <div class="metric-label">Memory Usage</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{{ total_requests }}</div>
                            <div class="metric-label">Total Requests</div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>System Metrics</h3>
                        <div class="metric">
                            <div class="metric-value">{{ current_tier|upper }}</div>
                            <div class="metric-label">Current Tier</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{{ max_load }}</div>
                            <div class="metric-label">Max Load Seen</div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>Raw Data</h3>
                        <pre style="background: #f6f6f7; padding: 15px; border-radius: 4px; overflow-x: auto;">{{ raw_data }}</pre>
                    </div>
                </div>
                
                <script>
                    // Auto-refresh every 30 seconds
                    setTimeout(function() {
                        location.reload();
                    }, 30000);
                </script>
            </body>
            </html>
            """
            
            # Prepare template variables
            cache_eff = cache_data.get('cache_efficiency', {})
            status = cache_data.get('status', 'unknown')
            
            template_vars = {
                'status': status,
                'status_class': 'healthy' if status == 'healthy' else 'warning' if status == 'degraded' else 'error',
                'hit_rate': int(cache_eff.get('hit_rate', 0)),
                'cache_size': cache_eff.get('cache_size', 0),
                'memory_usage': round(cache_eff.get('memory_usage_mb', 0.0), 2),
                'total_requests': cache_eff.get('total_requests', 0),
                'current_tier': cache_data.get('current_tier', 'unknown'),
                'max_load': cache_data.get('max_load_seen', 0.0),
                'raw_data': json.dumps(cache_data, indent=2)
            }
            
            return render_template_string(html_template, **template_vars)
            
        except Exception as e:
            error_logger.log_error(e, "ADMIN_PERFORMANCE_ERROR")
            return jsonify({'error': 'Failed to retrieve performance data'}), 500
    
    # Add Protected Customer Data compliance headers
    @app.after_request
    def add_gdpr_headers(response):
        """Add Shopify Protected Customer Data compliance headers"""
        try:
            response.headers['X-Shopify-Data-Protection'] = 'compliant'
            response.headers['X-Data-Minimization'] = 'enabled'
            response.headers['X-Customer-Privacy'] = 'protected'
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            # Shopify requires specific CSP headers for embedded apps
            # We must NOT set X-Frame-Options: DENY or SAMEORIGIN
            # Instead we use Content-Security-Policy frame-ancestors
            response.headers['Content-Security-Policy'] = "frame-ancestors https://*.myshopify.com https://admin.shopify.com;"
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            return response
        except Exception as e:
            logger.error(f"Error adding GDPR headers: {e}")
            return response


    # Add API routes
    @app.route('/api/process_orders')
    @verify_session_token
    @log_errors("API_PROCESS_ORDERS")
    def api_process_orders():
        """API endpoint for processing orders"""
        try:
            from flask import session
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"success": False, "error": "Not authenticated"}), 401
            
            from reporting import generate_orders_report
            result = generate_orders_report(user_id=user_id)
            return jsonify(result)
            
        except Exception as e:
            error_logger.log_error(e, "API_PROCESS_ORDERS")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/update_inventory')
    @verify_session_token
    @log_errors("API_UPDATE_INVENTORY")
    def api_update_inventory():
        """API endpoint for updating inventory"""
        try:
            from flask import session
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"success": False, "error": "Not authenticated"}), 401
            
            from reporting import generate_inventory_report
            result = generate_inventory_report(user_id=user_id)
            return jsonify(result)
            
        except Exception as e:
            error_logger.log_error(e, "API_UPDATE_INVENTORY")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/generate_report')
    @verify_session_token
    @log_errors("API_GENERATE_REPORT")
    def api_generate_report():
        """API endpoint for generating revenue report"""
        try:
            from flask import session
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"success": False, "error": "Not authenticated"}), 401
            
            from reporting import generate_report
            result = generate_report(user_id=user_id)
            return jsonify(result)
            
        except Exception as e:
            error_logger.log_error(e, "API_GENERATE_REPORT")
            return jsonify({"success": False, "error": str(e)}), 500




if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("ENVIRONMENT", "production") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug_mode, threaded=True)
