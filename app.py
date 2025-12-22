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
# CRITICAL: SameSite=None is REQUIRED for Shopify embedded apps (iframes)
# SameSite=Lax blocks cookies in cross-origin iframes, breaking session handling
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['REMEMBER_COOKIE_DURATION'] = 2592000  # 30 days
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'None'  # Also for remember me cookies
app.config['REMEMBER_COOKIE_SECURE'] = True  # Required when SameSite=None
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
        // Only load App Bridge CSS if in embedded mode
        if (new URLSearchParams(window.location.search).get('host')) {
            var link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = 'https://cdn.shopify.com/shopifycloud/app-bridge.css';
            document.head.appendChild(link);
        }
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

    <!-- Shopify App Bridge - Only load if embedded -->
    <script>
        (function() {
            // Only load App Bridge if we have host param (embedded mode)
            var urlParams = new URLSearchParams(window.location.search);
            var host = urlParams.get('host');
            
            if (!host) {
                // Not embedded, skip App Bridge
                return;
            }
            
            // Load App Bridge script
            var script = document.createElement('script');
            script.src = 'https://cdn.shopify.com/shopifycloud/app-bridge.js';
            script.onload = function() {
                initAppBridge();
            };
            document.head.appendChild(script);
            
            function initAppBridge() {
                try {
                    if (typeof window['app-bridge'] === 'undefined') {
                        setTimeout(initAppBridge, 50);
                        return;
                    }
                    
                    var AppBridge = window['app-bridge'];
                    if (!AppBridge || !AppBridge.default) {
                        setTimeout(initAppBridge, 50);
                        return;
                    }
                    
                    var createApp = AppBridge.default;
                    var urlParams = new URLSearchParams(window.location.search);
                    var shop = urlParams.get('shop') || '';
                    var host = urlParams.get('host') || '';
                    var apiKey = '{{ SHOPIFY_API_KEY or "" }}';
                    
                    // Decode host if base64
                    if (host && !host.includes('.')) {
                        try {
                            host = atob(host);
                        } catch(e) {}
                    }
                    
                    if (shop && host && apiKey) {
                        var app = createApp({
                            apiKey: apiKey,
                            host: host
                        });
                        
                        window.shopifyApp = app;
                        console.log('✅ App Bridge initialized');
                    }
                } catch (e) {
                    console.error('❌ App Bridge init failed:', e);
                }
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
        
        function showLoading(message = 'Processing...') {
            document.getElementById('output').innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <div class="loading-text">${message}</div>
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
            
            // Get session token if in embedded mode - seamless integration
            var fetchPromise;
            var isEmbedded = window.shopifyApp && new URLSearchParams(window.location.search).get('host');
            
            if (isEmbedded && window.shopifyApp) {
                // In embedded mode, we MUST have session token - retry up to 3 times
                var retryCount = 0;
                var maxRetries = 3;
                
                function getTokenWithRetry() {
                    return window.shopifyApp.getSessionToken().then(function(token) {
                        if (!token && retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve) {
                                setTimeout(function() {
                                    resolve(getTokenWithRetry());
                                }, 300);
                            });
                        }
                        return token;
                    });
                }
                
                fetchPromise = getTokenWithRetry().then(function(token) {
                    if (!token) {
                        throw new Error('Unable to get session token. Please refresh the page.');
                    }
                    return fetch('/api/process_orders', {
                        headers: {'Authorization': 'Bearer ' + token}
                    });
                }).catch(function(err) {
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
                fetchPromise = fetch('/api/process_orders');
            }
            
            fetchPromise
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
            
            // Get session token if in embedded mode - seamless integration
            var fetchPromise;
            var isEmbedded = window.shopifyApp && new URLSearchParams(window.location.search).get('host');
            
            if (isEmbedded && window.shopifyApp) {
                // In embedded mode, we MUST have session token - retry up to 3 times
                var retryCount = 0;
                var maxRetries = 3;
                
                function getTokenWithRetry() {
                    return window.shopifyApp.getSessionToken().then(function(token) {
                        if (!token && retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve) {
                                setTimeout(function() {
                                    resolve(getTokenWithRetry());
                                }, 300);
                            });
                        }
                        return token;
                    });
                }
                
                fetchPromise = getTokenWithRetry().then(function(token) {
                    if (!token) {
                        throw new Error('Unable to get session token. Please refresh the page.');
                    }
                    return fetch('/api/update_inventory', {
                        headers: {'Authorization': 'Bearer ' + token}
                    });
                }).catch(function(err) {
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
                fetchPromise = fetch('/api/update_inventory');
            }
            
            fetchPromise
                .then(r => {
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
            
            // Get session token if in embedded mode - seamless integration
            var fetchPromise;
            var isEmbedded = window.shopifyApp && new URLSearchParams(window.location.search).get('host');
            
            if (isEmbedded && window.shopifyApp) {
                // In embedded mode, we MUST have session token - retry up to 3 times
                var retryCount = 0;
                var maxRetries = 3;
                
                function getTokenWithRetry() {
                    return window.shopifyApp.getSessionToken().then(function(token) {
                        if (!token && retryCount < maxRetries) {
                            retryCount++;
                            return new Promise(function(resolve) {
                                setTimeout(function() {
                                    resolve(getTokenWithRetry());
                                }, 300);
                            });
                        }
                        return token;
                    });
                }
                
                fetchPromise = getTokenWithRetry().then(function(token) {
                    if (!token) {
                        throw new Error('Unable to get session token. Please refresh the page.');
                    }
                    return fetch('/api/generate_report', {
                        headers: {'Authorization': 'Bearer ' + token}
                    });
                }).catch(function(err) {
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
                fetchPromise = fetch('/api/generate_report');
            }
            
            fetchPromise
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
    shop = request.args.get('shop')
    embedded = request.args.get('embedded')
    host = request.args.get('host')
    
    # If embedded app request, DON'T redirect - render dashboard directly to avoid breaking iframe
    # Redirects in iframes can cause "refused to connect" errors
    # Also check Referer header as Shopify sends requests from admin.shopify.com
    referer = request.headers.get('Referer', '')
    is_from_shopify_admin = 'admin.shopify.com' in referer
    
    # CRITICAL: For embedded apps, ALWAYS render something - never redirect
    # Even if user isn't authenticated, show a page that handles it
    if embedded == '1' or shop or host or is_from_shopify_admin:
        # For embedded apps, check if store is connected
        from models import ShopifyStore
        store = None
        if shop:
            store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
        
        if store:
            # Store is connected - auto-login the user
            user = store.user
            if user and not current_user.is_authenticated:
                login_user(user, remember=True)
                session.permanent = True
                logger.info(f"Auto-logged in user for embedded app: {shop}")
        
        # For embedded apps, ALWAYS render dashboard - don't check Flask-Login
        # Flask-Login sessions don't work in iframes, but session tokens do
        # If user isn't logged in via Flask-Login, we'll handle it in the template
        # CRITICAL: Always render HTML for embedded apps, never redirect
        if True:  # Always render for embedded apps
            # Import dashboard function logic to render directly
            from flask import render_template_string
            
            # Safe defaults for when user isn't authenticated via Flask-Login
            # Session tokens will handle auth for API calls
            if current_user.is_authenticated:
                has_access = current_user.has_access()
                trial_active = current_user.is_trial_active()
                days_left = (current_user.trial_ends_at - datetime.utcnow()).days if trial_active else 0
                is_subscribed = current_user.is_subscribed
                user_id = current_user.id
            else:
                # User not authenticated via Flask-Login (normal for embedded apps)
                # Use safe defaults - session tokens will handle API auth
                has_access = False
                trial_active = False
                days_left = 0
                is_subscribed = False
                user_id = None
            
            from models import ShopifyStore
            has_shopify = False
            if user_id:
                has_shopify = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first() is not None
            elif shop:
                # Check if store exists even without user auth
                has_shopify = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first() is not None
            
            # Skip slow API calls for embedded apps - just show empty stats
            # This prevents the page from hanging while waiting for Shopify API
            quick_stats = {'has_data': False, 'pending_orders': 0, 'total_products': 0, 'low_stock_items': 0}
            # Don't fetch quick stats on initial load - let the user click buttons to load data
            # This makes the page load instantly
            
            shop_domain = shop or ''
            if has_shopify and user_id:
                store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
                if store:
                    shop_domain = store.shop_url
            elif shop:
                store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
                if store:
                    shop_domain = store.shop_url
            
            return render_template_string(DASHBOARD_HTML, 
                                         trial_active=trial_active, 
                                         days_left=days_left, 
                                         is_subscribed=is_subscribed, 
                                         has_shopify=has_shopify, 
                                         has_access=has_access,
                                         quick_stats=quick_stats,
                                         shop_domain=shop_domain,
                                         SHOPIFY_API_KEY=os.getenv('SHOPIFY_API_KEY', ''))
        else:
            # Not logged in - for embedded apps, render dashboard with connect prompt
            # DON'T redirect - just show the dashboard with a connect button
            # This prevents iframe breaking
            logger.info(f"Store not connected for embedded app: {shop}, showing dashboard with connect prompt")
            
            # Render dashboard with safe defaults (no auth required)
            from flask import render_template_string
            has_access = False
            trial_active = False
            days_left = 0
            is_subscribed = False
            has_shopify = False
            quick_stats = {'has_data': False, 'pending_orders': 0, 'total_products': 0, 'low_stock_items': 0}
            shop_domain = shop or ''
            
            return render_template_string(DASHBOARD_HTML, 
                                         trial_active=trial_active, 
                                         days_left=days_left, 
                                         is_subscribed=is_subscribed, 
                                         has_shopify=has_shopify, 
                                         has_access=has_access,
                                         quick_stats=quick_stats,
                                         shop_domain=shop_domain,
                                         SHOPIFY_API_KEY=os.getenv('SHOPIFY_API_KEY', ''))
    
    # Regular (non-embedded) request handling
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    # For standalone access, redirect to Shopify OAuth install instead of login
    # OAuth users don't have passwords, so login page won't work for them
    # Show a page that explains they need to install via Shopify
    from flask import render_template_string
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
    is_from_shopify_admin = 'admin.shopify.com' in referer
    shop = request.args.get('shop')
    host = request.args.get('host')
    is_embedded = request.args.get('embedded') == '1' or shop or host or is_from_shopify_admin
    
    # For embedded apps, allow access without strict auth (App Bridge handles it)
    # For regular requests, require login
    if not is_embedded and not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    # If embedded but not logged in, try to auto-login from shop param
    if is_embedded and not current_user.is_authenticated:
        if shop:
            from models import ShopifyStore
            store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
            if store and store.user:
                login_user(store.user, remember=True)
                session.permanent = True
                logger.info(f"Auto-logged in user for embedded app: {shop}")
    
    # For embedded requests, always render - never redirect
    # This prevents iframe breaking
    """Dashboard - accessible to all authenticated users, shows subscribe prompt if no access"""
    
    # Handle case where user might not be authenticated (for embedded apps)
    if current_user.is_authenticated:
        has_access = current_user.has_access()
        trial_active = current_user.is_trial_active()
        days_left = (current_user.trial_ends_at - datetime.utcnow()).days if trial_active else 0
    else:
        # Embedded app without auth - show limited view
        has_access = False
        trial_active = False
        days_left = 0
    
    # Check if user has connected Shopify
    from models import ShopifyStore
    if current_user.is_authenticated:
        has_shopify = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first() is not None
        is_subscribed = current_user.is_subscribed
    else:
        # For embedded apps without auth, check by shop param
        has_shopify = False
        if shop:
            store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
            if store:
                has_shopify = True
        is_subscribed = False
    
    # Skip slow API calls on dashboard load - just show empty stats
    # This prevents the page from hanging while waiting for Shopify API
    # Users can click buttons to load data when they need it
    quick_stats = {'has_data': False, 'pending_orders': 0, 'total_products': 0, 'low_stock_items': 0}
    
    # Get shop domain and API key for App Bridge initialization
    shop_domain = shop or ''
    if current_user.is_authenticated and has_shopify:
        store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
        if store:
            shop_domain = store.shop_url
    elif shop and has_shopify:
        store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
        if store:
            shop_domain = store.shop_url
    
    return render_template_string(DASHBOARD_HTML, 
                                 trial_active=trial_active, 
                                 days_left=days_left, 
                                 is_subscribed=is_subscribed, 
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

def get_authenticated_user():
    """
    Get authenticated user from either Flask-Login or Shopify session token.
    Returns (user, error_response) tuple. If user is None, error_response contains the error.
    """
    # Try Flask-Login first (for standalone access)
    if current_user.is_authenticated:
        return current_user, None
    
    # Try session token (for embedded apps)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        try:
            token = auth_header.split(' ')[1] if ' ' in auth_header else None
            if not token:
                return None, (jsonify({'error': 'Invalid token format', 'success': False}), 401)
            
            # Properly verify JWT token with full validation
            import jwt
            payload = jwt.decode(
                token,
                os.getenv('SHOPIFY_API_SECRET'),
                algorithms=['HS256'],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["iss", "dest", "aud", "sub", "exp", "nbf", "iat"]
                }
            )
            
            # Verify audience matches API key
            if payload.get('aud') != os.getenv('SHOPIFY_API_KEY'):
                logger.warning(f"Invalid audience in session token: {payload.get('aud')}")
                return None, (jsonify({'error': 'Invalid token', 'success': False}), 401)
            
            # Extract shop domain
            dest = payload.get('dest', '')
            if not dest or not dest.endswith('.myshopify.com'):
                logger.warning(f"Invalid destination in session token: {dest}")
                return None, (jsonify({'error': 'Invalid token', 'success': False}), 401)
            
            shop_domain = dest.replace('https://', '').split('/')[0]
            
            # Find user from shop
            from models import ShopifyStore
            store = ShopifyStore.query.filter_by(shop_url=shop_domain, is_active=True).first()
            if store and store.user:
                return store.user, None
            else:
                logger.warning(f"No store found for shop: {shop_domain}")
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
    except Exception as e:
        logger.error(f"Error processing orders for user {user_id}: {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to process orders: {str(e)}", "success": False}), 500

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
        clear_cache('get_products')
        result = update_inventory()
        if isinstance(result, dict):
            # Store inventory data in session for CSV export
            if result.get('success') and 'inventory_data' in result:
                from flask import session
                session['inventory_data'] = result['inventory_data']
            return jsonify(result)
        else:
            return jsonify({"success": False, "error": str(result)})
    except Exception as e:
        logger.error(f"Error updating inventory for user {user_id}: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": f"Failed to update inventory: {str(e)}"}), 500

@app.route('/api/generate_report', methods=['GET', 'POST'])
def api_generate_report():
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
    
    # Set current_user for generate_report() function
    from flask_login import login_user
    login_user(user, remember=False)
    
    logger.info(f"Generate report called by user {user_id}")
    try:
        from reporting import generate_report
        # Pass user_id to avoid recursion
        data = generate_report(user_id=user_id)
        if data.get('error') and data['error'] is not None:
            error_msg = data['error']
            if 'No Shopify store connected' in error_msg:
                logger.info(f"Generate report: No store connected for user {user_id}")
            else:
                logger.error(f"Generate report error for user {user_id}: {error_msg}")
            return error_msg, 500
        
        if not data.get('message'):
            logger.warning(f"Generate report returned no message for user {user_id}")
            return '<h3 class="error">❌ No report data available</h3>', 500
        
        html = data.get('message', '<h3 class="error">❌ No report data available</h3>')
        
        from flask import session
        if 'report_data' in data:
            session['report_data'] = data['report_data']
        
        return html, 200
    except Exception as e:
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
