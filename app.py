from flask import Flask, jsonify, render_template_string, redirect, url_for, request, session
from flask_login import LoginManager, login_required, current_user, login_user
from flask_bcrypt import Bcrypt
from flask_session import Session
import os
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
from performance import compress_response, clear_cache

# Initialize Sentry for error monitoring (if DSN is provided)
sentry_dsn = os.getenv('SENTRY_DSN')
if sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FlaskIntegration(),
            SqlalchemyIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
        ],
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        profiles_sample_rate=0.1,  # 10% of transactions for profiling
        environment=os.getenv('ENVIRONMENT', 'production'),
        release=os.getenv('RELEASE_VERSION', '1.0.0'),
        before_send=lambda event, hint: event if os.getenv('ENVIRONMENT') != 'development' else None,  # Don't send in dev
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
app.config['SESSION_COOKIE_SECURE'] = True  # Secure cookies over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['REMEMBER_COOKIE_DURATION'] = 2592000  # 30 days
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///employeesuite.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Performance optimizations
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,  # Increased for 50-100 clients
    'max_overflow': 20,  # Increased for traffic spikes
    'pool_pre_ping': True,  # Verify connections before using
    'pool_recycle': 3600,  # Recycle connections after 1 hour
}

db.init_app(app)

# Configure server-side sessions
# Session config removed - using Flask defaults

app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 30
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

# Initialize rate limiter with global 200 req/hour
limiter = init_limiter(app)

# Apply security headers and compression to all responses
@app.after_request
def optimize_response(response):
    """Add security headers and compress responses"""
    response = add_security_headers(response)
    response = compress_response(response)
    
    # Enable Keep-Alive for webhook endpoints (Shopify requirement)
    # This allows Shopify to reuse connections, reducing latency
    if request.path.startswith('/webhooks/'):
        response.headers['Connection'] = 'keep-alive'
        response.headers['Keep-Alive'] = 'timeout=5, max=1000'
    
    # Add cache headers for static assets
    if request.endpoint == 'static':
        response.cache_control.max_age = 31536000  # 1 year
        response.cache_control.public = True
    return response

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
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <!-- Shopify Polaris CSS for better design consistency -->
    <link rel="stylesheet" href="https://cdn.shopify.com/shopifycloud/app-bridge.css">
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
        }
        
        /* Header - Shopify Style */
        .header {
            background: #ffffff;
            border-bottom: 1px solid #e1e3e5;
            position: sticky;
            top: 0;
            z-index: 100;
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
        
        /* Page Title - Shopify Typography */
        .page-title {
            font-size: 28px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 8px;
            letter-spacing: -0.3px;
            line-height: 1.2;
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

    <!-- Shopify App Bridge (for embedded apps) -->
    <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
    <script>
        // Initialize App Bridge for embedded apps
        if (window['app-bridge']) {
            var AppBridge = window['app-bridge'];
            var createApp = AppBridge.default;
            
            // Get shop and host from URL params (Shopify provides these for embedded apps)
            var urlParams = new URLSearchParams(window.location.search);
            var shop = urlParams.get('shop') || '{{ shop_domain or "" }}';
            var host = urlParams.get('host') || '';
            var apiKey = '{{ SHOPIFY_API_KEY or "" }}';
            
            // Only initialize if we have the required params (embedded app)
            if (shop && host && apiKey) {
                try {
                    var app = createApp({
                        apiKey: apiKey,
                        host: host,
                        shop: shop
                    });
                    
                    // Make app available globally
                    window.shopifyApp = app;
                    
                    // Fetch and send session tokens for all API requests (MANDATORY as of Jan 2025)
                    app.getSessionToken().then(function(token) {
                        // Set default Authorization header for all fetch requests
                        var originalFetch = window.fetch;
                        window.fetch = function(url, options) {
                            options = options || {};
                            options.headers = options.headers || {};
                            if (!options.headers['Authorization'] && token) {
                                options.headers['Authorization'] = 'Bearer ' + token;
                            }
                            return originalFetch(url, options);
                        };
                    }).catch(function(error) {
                        console.warn('Failed to get session token:', error);
                    });
                } catch (e) {
                    console.warn('App Bridge initialization failed:', e);
                }
            }
        }
    </script>
    
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-RBBQ4X7FJ3"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', 'G-RBBQ4X7FJ3');
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
        
        <div class="output-container">
            <div class="output-header">Results</div>
            <div id="output"></div>
        </div>
    </div>
    
    <script>
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
        
        function showLoading() {
            document.getElementById('output').innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <div class="loading-text">Processing...</div>
                </div>
            `;
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
            setButtonLoading(button, true);
            showLoading();
            fetch('/api/process_orders')
                .then(r => {
                    if (!r.ok) throw new Error('Network error');
                    return r.json();
                })
                .then(d => {
                    setButtonLoading(button, false);
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
                        // For errors, display the backend HTML directly (it already has the title and banner)
                        document.getElementById('output').innerHTML = `<div style="animation: fadeIn 0.3s ease-in;">${d.error || d.message || 'No details available'}</div>`;
                    }
                })
                .catch(err => {
                    setButtonLoading(button, false);
                    document.getElementById('output').innerHTML = `
                        <div style="animation: fadeIn 0.3s ease-in;">
                            <h3 class="error">❌ Connection Error</h3>
                            <p style="margin-top: 12px;">Unable to connect to server. Please check your internet connection and try again.</p>
                            <p style="margin-top: 8px; font-size: 13px; color: #737373;">💡 Tip: If this persists, go to Settings and verify your Shopify store is connected.</p>
                        </div>
                    `;
                });
        }
        
        function updateInventory(button) {
            setButtonLoading(button, true);
            showLoading();
            fetch('/api/update_inventory')
                .then(r => {
                    if (!r.ok) throw new Error('Network error');
                    return r.json();
                })
                .then(d => {
                    setButtonLoading(button, false);
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
                        // For errors, display the backend HTML directly (it already has the title and banner)
                        document.getElementById('output').innerHTML = `<div style="animation: fadeIn 0.3s ease-in;">${d.error || d.message || 'No details available'}</div>`;
                    }
                })
                .catch(err => {
                    setButtonLoading(button, false);
                    document.getElementById('output').innerHTML = `
                        <div style="animation: fadeIn 0.3s ease-in;">
                            <h3 class="error">❌ Connection Error</h3>
                            <p style="margin-top: 12px;">Unable to connect to server. Please check your internet connection and try again.</p>
                            <p style="margin-top: 8px; font-size: 13px; color: #737373;">💡 Tip: If this persists, go to Settings and verify your Shopify store is connected.</p>
                        </div>
                    `;
                });
        }
        
        function generateReport(button) {
            setButtonLoading(button, true);
            showLoading();
            fetch('/api/generate_report')
                .then(r => {
                    if (!r.ok) {
                        // If error response, try to get error HTML
                        return r.text().then(html => {
                            throw new Error(html);
                        });
                    }
                    return r.text();
                })
                .then(html => {
                    setButtonLoading(button, false);
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
                    setButtonLoading(button, false);
                    // Check if error message is HTML (from backend) or plain text (network error)
                    if (err.message && err.message.includes('Error Loading revenue')) {
                        // Backend error HTML
                        document.getElementById('output').innerHTML = `<div style="animation: fadeIn 0.3s ease-in;">${err.message}</div>`;
                    } else {
                        // Network error
                        document.getElementById('output').innerHTML = `
                            <div style="animation: fadeIn 0.3s ease-in;">
                                <h3 class="error">❌ Error Loading revenue</h3>
                                <p style="margin-top: 12px;">Unable to generate report. Please check your internet connection and try again.</p>
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
                processOrders();
                {% else %}
                showSubscribePrompt();
                {% endif %}
            }
            // Ctrl/Cmd + 2 = Check Inventory
            if ((e.ctrlKey || e.metaKey) && e.key === '2') {
                e.preventDefault();
                {% if has_access %}
                updateInventory();
                {% else %}
                showSubscribePrompt();
                {% endif %}
            }
            // Ctrl/Cmd + 3 = Generate Report
            if ((e.ctrlKey || e.metaKey) && e.key === '3') {
                e.preventDefault();
                {% if has_access %}
                generateReport();
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
    """Home page - handles embedded app requests and redirects appropriately"""
    # Check if this is an embedded app request from Shopify
    id_token = request.args.get('id_token')
    shop = request.args.get('shop')
    embedded = request.args.get('embedded')
    
    # If embedded app request with id_token, verify and handle
    if embedded == '1' and id_token and shop:
        try:
            import jwt
            SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
            SHOPIFY_API_SECRET = os.getenv('SHOPIFY_API_SECRET')
            
            if SHOPIFY_API_SECRET:
                # Verify the id_token (session token)
                payload = jwt.decode(
                    id_token,
                    SHOPIFY_API_SECRET,
                    algorithms=['HS256'],
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_iat": True,
                        "require": ["iss", "dest", "aud", "sub", "exp", "nbf", "iat"]
                    }
                )
                
                # Verify audience matches API key
                if payload.get('aud') == SHOPIFY_API_KEY:
                    # Check if store is already connected
                    from models import ShopifyStore
                    store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
                    
                    if store:
                        # Store is connected - auto-login the user
                        user = store.user
                        if user:
                            login_user(user, remember=True)
                            session.permanent = True
                            logger.info(f"Auto-logged in user for embedded app: {shop}")
                            return redirect(url_for('dashboard'))
                    
                    # Store not connected - redirect to OAuth install
                    logger.info(f"Store not connected for embedded app: {shop}, redirecting to install")
                    return redirect(url_for('oauth.install', shop=shop))
        except jwt.ExpiredSignatureError:
            logger.warning("Expired id_token in embedded app request")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid id_token in embedded app request: {e}")
        except Exception as e:
            logger.error(f"Error handling embedded app request: {e}", exc_info=True)
    
    # Regular (non-embedded) request handling
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('auth.login'))

# Icon is served via Flask static file serving automatically

@app.route('/dashboard')
@verify_session_token
@login_required
def dashboard():
    """Dashboard - accessible to all authenticated users, shows subscribe prompt if no access"""
    has_access = current_user.has_access()
    trial_active = current_user.is_trial_active()
    days_left = (current_user.trial_ends_at - datetime.utcnow()).days if trial_active else 0
    
    # Check if user has connected Shopify
    from models import ShopifyStore
    has_shopify = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first() is not None
    
    # Get quick stats for dashboard (if has access and Shopify connected)
    quick_stats = {'has_data': False, 'pending_orders': 0, 'total_products': 0, 'low_stock_items': 0}
    if has_access and has_shopify:
        try:
            from shopify_integration import ShopifyClient
            store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
            if store:
                client = ShopifyClient(store.shop_url, store.access_token)
                # Quick stats - fast API calls
                orders = client.get_orders(status='any', limit=10)  # Just first 10 for speed
                products = client.get_products()
                low_stock = client.get_low_stock(threshold=10)
                
                # Handle None values and error dicts properly
                if orders is not None and not isinstance(orders, dict) and isinstance(orders, list):
                    quick_stats['pending_orders'] = len([o for o in orders if o and isinstance(o, dict) and o.get('status') in ['PENDING', 'AUTHORIZED']])
                
                if products is not None and not isinstance(products, dict) and isinstance(products, list):
                    quick_stats['total_products'] = len(products)
                
                if low_stock is not None and not isinstance(low_stock, dict) and isinstance(low_stock, list):
                    quick_stats['low_stock_items'] = len(low_stock)
                
                # Only set has_data if we got valid data
                if quick_stats['pending_orders'] > 0 or quick_stats['total_products'] > 0:
                    quick_stats['has_data'] = True
        except Exception as e:
            logger.warning(f"Error fetching quick stats: {e}")
            quick_stats = {'has_data': False, 'pending_orders': 0, 'total_products': 0, 'low_stock_items': 0}
    
    # Get shop domain and API key for App Bridge initialization
    shop_domain = ''
    if has_shopify:
        store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
        if store:
            shop_domain = store.shop_url
    
    return render_template_string(DASHBOARD_HTML, 
                                 trial_active=trial_active, 
                                 days_left=days_left, 
                                 is_subscribed=current_user.is_subscribed, 
                                 has_shopify=has_shopify, 
                                 has_access=has_access,
                                 quick_stats=quick_stats,
                                 shop_domain=shop_domain,
                                 SHOPIFY_API_KEY=os.getenv('SHOPIFY_API_KEY', ''))


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
    try:
        # Quick DB connectivity check
        db.session.execute(db.text('SELECT 1'))
        return jsonify({
            "status": "healthy", 
            "service": "Employee Suite", 
            "version": "2.0", 
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/api/docs')
def api_docs():
    """API documentation endpoint"""
    return redirect('https://github.com/vyndigital-cloud/EmployeeSuite-Production/blob/main/API_DOCUMENTATION.md')

@app.route('/api/process_orders', methods=['GET', 'POST'])
@login_required
@require_access
def api_process_orders():
    try:
        result = process_orders()
        if isinstance(result, dict):
            return jsonify(result)
        else:
            return jsonify({"message": str(result), "success": True})
    except Exception as e:
        logger.error(f"Error processing orders for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to process orders: {str(e)}", "success": False}), 500

@app.route('/api/update_inventory', methods=['GET', 'POST'])
@login_required
@require_access
def api_update_inventory():
    try:
        # Clear inventory cache to force fresh data
        clear_cache('get_products')
        result = update_inventory()
        if isinstance(result, dict):
            return jsonify(result)
        else:
            return jsonify({"success": False, "error": str(result)})
    except Exception as e:
        logger.error(f"Error updating inventory for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": f"Failed to update inventory: {str(e)}"}), 500

@app.route('/api/generate_report', methods=['GET', 'POST'])
@login_required
@require_access
def api_generate_report():
    logger.info(f"Generate report called by user {current_user.id}")
    try:
        from reporting import generate_report
        data = generate_report()
        if data.get('error') and data['error'] is not None:
            # Don't log expected errors (like "No Shopify store connected") as ERROR level
            error_msg = data['error']
            if 'No Shopify store connected' in error_msg:
                logger.info(f"Generate report: No store connected for user {current_user.id}")
            else:
                logger.error(f"Generate report error for user {current_user.id}: {error_msg}")
            # Return the formatted error HTML directly (it already has the title and banner)
            return error_msg, 500
        
        # Report HTML is already in data['message']
        if not data.get('message'):
            logger.warning(f"Generate report returned no message for user {current_user.id}")
            return '<h3 class="error">❌ No report data available</h3>', 500
        
        # Export button is now included directly in the report HTML from reporting.py
        html = data.get('message', '<h3 class="error">❌ No report data available</h3>')
        
        # Store report data for CSV export
        from flask import session
        if 'report_data' in data:
            session['report_data'] = data['report_data']
        
        return html
    except Exception as e:
        logger.error(f"Generate report exception for user {current_user.id}: {str(e)}", exc_info=True)
        return f"<h3 class='error'>❌ Error: {str(e)}</h3>", 500

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
            try:
                from migrate_shopify_store_columns import migrate_shopify_store_columns
                migrate_shopify_store_columns(app, db)
            except Exception as e:
                logger.warning(f"Could not migrate shopify_stores columns via function: {e}")
                # Try manual migration as fallback (SQLite-compatible)
                try:
                    logger.info("Adding shop_id, charge_id, uninstalled_at columns (fallback)...")
                    columns = [
                        ("shop_id", "BIGINT"),
                        ("charge_id", "VARCHAR(255)"),
                        ("uninstalled_at", "TIMESTAMP")
                    ]
                    for col_name, col_type in columns:
                        try:
                            db.session.execute(db.text(f"""
                                ALTER TABLE shopify_stores 
                                ADD COLUMN {col_name} {col_type}
                            """))
                        except Exception as col_error:
                            error_str = str(col_error).lower()
                            if "duplicate column" in error_str or "already exists" in error_str:
                                logger.info(f"✅ {col_name} column already exists")
                            else:
                                raise
                    db.session.commit()
                    logger.info("✅ shopify_stores columns added successfully")
                except Exception as migrate_error:
                    error_str = str(migrate_error).lower()
                    if "duplicate column" in error_str or "already exists" in error_str:
                        logger.info("✅ shopify_stores columns already exist")
                    else:
                        logger.warning(f"Could not add shopify_stores columns: {migrate_error}")
                    db.session.rollback()
            
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
