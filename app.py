from flask import Flask, jsonify, render_template_string, redirect, url_for, request
from flask_login import LoginManager, login_required, current_user
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
from order_processing import process_orders
from inventory import update_inventory
from reporting import generate_report

from logging_config import logger
from access_control import require_access
from security_enhancements import (
    add_security_headers, 
    check_request_size, 
    sanitize_input_enhanced,
    validate_request,
    log_security_event,
    require_https
)

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
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = True  # Secure cookies over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['REMEMBER_COOKIE_DURATION'] = 2592000  # 30 days
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///employeesuite.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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

# Apply security headers to all responses
@app.after_request
def security_headers(response):
    """Add security headers to all responses"""
    return add_security_headers(response)

# Request validation before processing
@app.before_request
def validate_request_security():
    """Validate incoming requests for security"""
    # Skip validation for static files and health checks
    if request.endpoint in ('static', 'health'):
        return
    
    # Check request size
    if not check_request_size():
        return jsonify({'error': 'Request too large'}), 413
    
    # Validate request
    is_valid, issues = validate_request()
    if not is_valid:
        log_security_event('request_validation_failed', str(issues), 'WARNING')
        return jsonify({'error': 'Invalid request'}), 400

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
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            color: #171717;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        /* Header */
        .header {
            background: #fff;
            border-bottom: 1px solid #e5e5e5;
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
            font-size: 18px;
            font-weight: 600;
            color: #171717;
            transition: opacity 0.2s;
        }
        .logo:hover {
            opacity: 0.8;
        }
        .header-nav {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .nav-btn {
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            border: none;
            cursor: pointer;
            transition: background 0.2s;
            background: transparent;
            color: #525252;
        }
        .nav-btn:hover {
            background: #f5f5f5;
        }
        .nav-btn-primary {
            background: #4a7338;
            color: #fff;
        }
        .nav-btn-primary:hover {
            background: #3a5c2a;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(74, 115, 56, 0.3);
        }
        
        /* Container */
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 48px 24px;
        }
        
        /* Page Title */
        .page-title {
            font-size: 36px;
            font-weight: 700;
            color: #0a0a0a;
            margin-bottom: 10px;
            letter-spacing: -1px;
        }
        .page-subtitle {
            font-size: 17px;
            color: #737373;
            margin-bottom: 48px;
            font-weight: 400;
            line-height: 1.6;
            max-width: 800px;
        }
        
        /* Trial Banner */
        .banner {
            background: #fafafa;
            border: 1px solid #e5e5e5;
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: none;
        }
        .banner-warning {
            border-left: 3px solid #72b05e;
        }
        .banner-info {
            border-left: 3px solid #4a7338;
        }
        .banner-content h3 {
            font-size: 16px;
            font-weight: 700;
            color: #0a0a0a;
            margin-bottom: 6px;
            letter-spacing: -0.2px;
        }
        .banner-content p {
            font-size: 15px;
            color: #737373;
            font-weight: 400;
        }
        .banner-action {
            background: #4a7338;
            color: #fff;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            white-space: nowrap;
            transition: all 0.2s ease;
        }
        .banner-action:hover {
            background: #3a5c2a;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(74, 115, 56, 0.3);
        }
        
        /* Cards Grid */
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }
        .card {
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 12px;
            padding: 28px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            transition: all 0.2s ease;
        }
        .card:hover {
            border-color: #d4d4d4;
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
            transform: translateY(-2px);
        }
        .card:active {
            transform: translateY(0);
        }
        .card-icon {
            font-size: 32px;
            margin-bottom: 16px;
            line-height: 1;
            filter: grayscale(0%);
            transition: transform 0.2s ease;
        }
        .card:hover .card-icon {
            transform: scale(1.1);
        }
        .card-title {
            font-size: 20px;
            font-weight: 700;
            color: #0a0a0a;
            margin-bottom: 10px;
            letter-spacing: -0.3px;
        }
        .card-description {
            font-size: 15px;
            color: #737373;
            line-height: 1.7;
            margin-bottom: 24px;
            font-weight: 400;
            min-height: 48px;
        }
        .card-btn {
            width: 100%;
            background: #171717;
            color: #fff;
            border: none;
            padding: 14px;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            letter-spacing: 0.3px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .card-btn:hover {
            background: #262626;
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
        }
        .card-btn:active {
            transform: translateY(0);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        }
        .card-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none !important;
        }
        
        /* Output */
        .output-container {
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        .output-header {
            padding: 18px 24px;
            border-bottom: 1px solid #e5e5e5;
            font-size: 15px;
            font-weight: 600;
            color: #171717;
            letter-spacing: 0;
        }
        #output {
            padding: 24px;
            min-height: 200px;
            font-size: 14px;
            line-height: 1.8;
            color: #525252;
            font-family: 'SF Mono', monospace;
        }
        #output:empty:before {
            content: 'Results will appear here...';
            color: #a3a3a3;
            font-style: italic;
        }
        #output:empty {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        /* Loading */
        .loading {
            text-align: center;
            padding: 40px;
        }
        .spinner {
            width: 32px;
            height: 32px;
            border: 3px solid #f5f5f5;
            border-top: 3px solid #171717;
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
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .loading-text {
            font-size: 14px;
            color: #737373;
            animation: pulse 2s ease-in-out infinite;
        }
        
        /* Status */
        .success { color: #16a34a; font-weight: 500; }
        .error { color: #dc2626; font-weight: 500; }
        
        /* Smooth transitions */
        * {
            transition: background-color 0.2s ease, border-color 0.2s ease, transform 0.2s ease, opacity 0.2s ease;
        }
        
        /* Focus states for accessibility */
        button:focus-visible,
        a:focus-visible {
            outline: 2px solid #4a7338;
            outline-offset: 2px;
        }
        
        /* Print styles */
        @media print {
            .header, .banner, .card-btn, footer { display: none; }
            .card { break-inside: avoid; }
        }
        
        /* Responsive - Mobile First */
        @media (max-width: 768px) {
            .container { padding: 24px 16px; }
            .page-title { font-size: 28px; }
            .page-subtitle { font-size: 15px; }
            .cards-grid { grid-template-columns: 1fr; gap: 16px; }
            .banner { flex-direction: column; gap: 16px; text-align: center; padding: 16px 20px; }
            .banner-action { width: 100%; text-align: center; }
            .header-content { padding: 0 16px; }
            .header-nav { gap: 4px; }
            .nav-btn { padding: 6px 10px; font-size: 13px; }
            .card { padding: 20px; }
            .card-icon { font-size: 24px; }
            .card-title { font-size: 18px; }
            .card-description { font-size: 14px; }
            #output { padding: 16px; min-height: 150px; font-size: 13px; }
        }
        @media (max-width: 480px) {
            .page-title { font-size: 24px; }
            .logo { font-size: 16px; }
            .header-nav { flex-wrap: wrap; }
        }
    </style>

    <!-- Shopify App Bridge (for embedded apps) -->
    <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
    
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-RBBQ4X7FJ3"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', 'G-RBBQ4X7FJ3');
    </script>
    
    <!-- Meta tags for better SEO and sharing -->
    <meta name="description" content="Automate your Shopify store operations with real-time order processing, inventory management, and revenue analytics.">
    <meta name="keywords" content="shopify, automation, inventory, orders, analytics, ecommerce">
    <meta property="og:title" content="Employee Suite - Shopify Automation Platform">
    <meta property="og:description" content="Automate order processing, inventory management, and revenue reporting for your Shopify store.">
    <meta property="og:type" content="website">
    </head>
<body>
    <div class="header">
        <div class="header-content">
            <a href="/dashboard" style="text-decoration: none; color: inherit; display: flex; align-items: center; gap: 10px; font-weight: 600;" class="logo">
                <span style="font-size: 20px;">🚀</span>
                <span>Employee Suite</span>
            </a>
            <div class="header-nav">
                <a href="{{ url_for('shopify.shopify_settings') }}" class="nav-btn">Settings</a>
                <a href="{{ url_for('billing.subscribe') }}" class="nav-btn nav-btn-primary">Subscribe</a>
                <a href="/logout" class="nav-btn">Logout</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="page-title">Dashboard</div>
        <div class="page-subtitle">Automate your Shopify store operations with real-time inventory management, automated order processing, and comprehensive revenue analytics</div>
        
        {% if not has_access %}
        <div class="banner banner-warning" style="justify-content: space-between; align-items: center;">
            <div class="banner-content">
                <h3>Subscription Required</h3>
                <p>Your trial has ended. Subscribe now to continue using Employee Suite.</p>
            </div>
            <a href="{{ url_for('billing.subscribe') }}" class="banner-action">Subscribe Now</a>
        </div>
        {% elif trial_active and not is_subscribed %}
        <div class="banner banner-warning" style="justify-content: flex-start;">
            <div class="banner-content">
                <h3>Trial Active</h3>
                <p>{{ days_left }} day{{ 's' if days_left != 1 else '' }} remaining - Subscribe in the top right to keep access</p>
            </div>
        </div>
        {% endif %}
        
        {% if not has_shopify %}
        <div class="banner banner-info">
            <div class="banner-content">
                <h3>🚀 Get Started</h3>
                <p>Connect your Shopify store to unlock automated order processing, inventory management, and revenue analytics</p>
            </div>
            <a href="{{ url_for('shopify.shopify_settings') }}" class="banner-action">Connect Store</a>
        </div>
        {% endif %}
        
        <div class="cards-grid">
            <div class="card">
                <div class="card-icon">📦</div>
                <div class="card-title">Order Processing</div>
                <div class="card-description">Automatically process pending and unfulfilled Shopify orders. Sync order status in real-time.</div>
                {% if has_access %}
                <button class="card-btn" onclick="processOrders()" aria-label="Process pending orders">
                    Process Orders Now
                </button>
                {% else %}
                <button class="card-btn" onclick="showSubscribePrompt()" style="opacity: 0.6; cursor: not-allowed;" disabled aria-label="Subscribe to process orders">Process Orders</button>
                {% endif %}
            </div>
            
            <div class="card">
                <div class="card-icon">📊</div>
                <div class="card-title">Inventory Management</div>
                <div class="card-description">Monitor stock levels across all products. Get low-stock alerts and complete inventory visibility.</div>
                {% if has_access %}
                <button class="card-btn" onclick="updateInventory()" aria-label="Check inventory levels">
                    Check Inventory
                </button>
                {% else %}
                <button class="card-btn" onclick="showSubscribePrompt()" style="opacity: 0.6; cursor: not-allowed;" disabled aria-label="Subscribe to check inventory">Check Inventory</button>
                {% endif %}
            </div>
            
            <div class="card">
                <div class="card-icon">💰</div>
                <div class="card-title">Revenue Analytics</div>
                <div class="card-description">Generate comprehensive revenue reports with profit calculations and product performance insights.</div>
                {% if has_access %}
                <button class="card-btn" onclick="generateReport()" aria-label="Generate revenue report">
                    Generate Report
                </button>
                {% else %}
                <button class="card-btn" onclick="showSubscribePrompt()" style="opacity: 0.6; cursor: not-allowed;" disabled aria-label="Subscribe to generate reports">Generate Report</button>
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
                <div style="padding: 24px; background: #fef2f2; border-radius: 8px; border-left: 3px solid #dc2626;">
                    <h3 style="color: #dc2626; margin-bottom: 12px;">Subscription Required</h3>
                    <p style="color: #991b1b; margin-bottom: 16px;">Your trial has ended. Subscribe now to continue using Employee Suite features.</p>
                    <a href="{{ url_for('billing.subscribe') }}" style="display: inline-block; background: #4a7338; color: #fff; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: 600;">Subscribe Now</a>
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
        
        function processOrders() {
            showLoading();
            fetch('/api/process_orders')
                .then(r => {
                    if (!r.ok) throw new Error('Network error');
                    return r.json();
                })
                .then(d => {
                    const c = d.success ? 'success' : 'error';
                    const icon = d.success ? '✅' : '❌';
                    document.getElementById('output').innerHTML = `
                        <div style="animation: fadeIn 0.3s ease-in;">
                            <h3 class="${c}" style="display: flex; align-items: center; gap: 8px;">
                                <span>${icon}</span>
                                <span>${d.success ? 'Orders Processed Successfully' : 'Error Processing Orders'}</span>
                            </h3>
                            <p style="margin-top: 12px; line-height: 1.6;">${d.message || d.error || 'No details available'}</p>
                            ${d.success ? '<p style="margin-top: 8px; font-size: 13px; color: #737373;">✨ Your orders have been processed and synced.</p>' : ''}
                        </div>
                    `;
                })
                .catch(err => {
                    document.getElementById('output').innerHTML = `
                        <div style="animation: fadeIn 0.3s ease-in;">
                            <h3 class="error">❌ Connection Error</h3>
                            <p style="margin-top: 12px;">Unable to connect to server. Please check your internet connection and try again.</p>
                        </div>
                    `;
                });
        }
        
        function updateInventory() {
            showLoading();
            fetch('/api/update_inventory')
                .then(r => {
                    if (!r.ok) throw new Error('Network error');
                    return r.json();
                })
                .then(d => {
                    const c = d.success ? 'success' : 'error';
                    const icon = d.success ? '✅' : '❌';
                    document.getElementById('output').innerHTML = `
                        <div style="animation: fadeIn 0.3s ease-in;">
                            <h3 class="${c}" style="display: flex; align-items: center; gap: 8px;">
                                <span>${icon}</span>
                                <span>${d.success ? 'Inventory Updated' : 'Error Updating Inventory'}</span>
                            </h3>
                            <div style="margin-top: 12px; white-space: pre-wrap; line-height: 1.6;">${d.message || d.error || 'No details available'}</div>
                            ${d.success ? '<p style="margin-top: 8px; font-size: 13px; color: #737373;">🔄 Inventory data refreshed from Shopify.</p>' : ''}
                        </div>
                    `;
                })
                .catch(err => {
                    document.getElementById('output').innerHTML = `
                        <div style="animation: fadeIn 0.3s ease-in;">
                            <h3 class="error">❌ Connection Error</h3>
                            <p style="margin-top: 12px;">Unable to connect to server. Please check your internet connection and try again.</p>
                        </div>
                    `;
                });
        }
        
        function generateReport() {
            showLoading();
            fetch('/api/generate_report')
                .then(r => {
                    if (!r.ok) throw new Error('Network error');
                    return r.text();
                })
                .then(html => {
                    document.getElementById('output').innerHTML = `<div style="animation: fadeIn 0.3s ease-in;">${html}</div>`;
                })
                .catch(err => {
                    document.getElementById('output').innerHTML = `
                        <div style="animation: fadeIn 0.3s ease-in;">
                            <h3 class="error">❌ Connection Error</h3>
                            <p style="margin-top: 12px;">Unable to generate report. Please check your internet connection and try again.</p>
                        </div>
                    `;
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

    <footer style="margin-top: 80px; padding: 32px 24px; border-top: 1px solid #e5e5e5; text-align: center; background: #fafafa;">
        <div style="max-width: 1200px; margin: 0 auto;">
            <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; font-size: 14px; margin-bottom: 16px;">
                <a href="/faq" style="color: #525252; text-decoration: none; font-weight: 500; transition: color 0.2s;">FAQ</a>
                <span style="color: #d4d4d4;">|</span>
                <a href="/privacy" style="color: #525252; text-decoration: none; font-weight: 500; transition: color 0.2s;">Privacy Policy</a>
                <span style="color: #d4d4d4;">|</span>
                <a href="/terms" style="color: #525252; text-decoration: none; font-weight: 500; transition: color 0.2s;">Terms of Service</a>
            </div>
            <div style="color: #737373; font-size: 13px;">
                © 2025 Employee Suite. All rights reserved.
            </div>
        </div>
    </footer>
</body>
</html>
"""

@app.route('/')
def home():
    """Home page - redirects to dashboard if authenticated, login if not"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('auth.login'))

# Icon is served via Flask static file serving automatically

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard - accessible to all authenticated users, shows subscribe prompt if no access"""
    has_access = current_user.has_access()
    trial_active = current_user.is_trial_active()
    days_left = (current_user.trial_ends_at - datetime.utcnow()).days if trial_active else 0
    
    # Check if user has connected Shopify
    from models import ShopifyStore
    has_shopify = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first() is not None
    
    # Get some stats for better UX (if has access)
    stats = {}
    if has_access and has_shopify:
        try:
            store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
            if store:
                from shopify_integration import ShopifyClient
                client = ShopifyClient(store.shop_url, store.access_token)
                # Quick stats (non-blocking, won't fail if API is slow)
                stats['has_data'] = True
        except:
            stats['has_data'] = False
    
    return render_template_string(DASHBOARD_HTML, 
                                 trial_active=trial_active, 
                                 days_left=days_left, 
                                 is_subscribed=current_user.is_subscribed, 
                                 has_shopify=has_shopify, 
                                 has_access=has_access)


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
        result = update_inventory()
        if isinstance(result, dict) and result.get("success"):
            return jsonify(result)
        else:
            return jsonify({"success": False, "error": str(result)})
    except Exception as e:
        logger.error(f"Error updating inventory for user {current_user.id}: {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to update inventory: {str(e)}", "success": False}), 500

@app.route('/api/generate_report', methods=['GET', 'POST'])
@login_required
@require_access
def api_generate_report():
    logger.info(f"Generate report called by user {current_user.id}")
    try:
        from reporting import generate_report
        data = generate_report()
        if data.get('error') and data['error'] is not None:
            logger.error(f"Generate report error for user {current_user.id}: {data['error']}")
            return f"<h3 class='error'>❌ Error: {data['error']}</h3>", 500
        
        # Report HTML is already in data['message']
        if not data.get('message'):
            logger.warning(f"Generate report returned no message for user {current_user.id}")
            return '<h3 class="error">❌ No report data available</h3>', 500
        
        return data.get('message', '<h3 class="error">❌ No report data available</h3>')
    except Exception as e:
        logger.error(f"Generate report exception for user {current_user.id}: {str(e)}", exc_info=True)
        return f"<h3 class='error'>❌ Error: {str(e)}</h3>", 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found", "status": 404}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error", "status": 500}), 500

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
