from flask import Flask, jsonify, render_template_string, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_session import Session
import os
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
from order_processing import process_orders
from inventory import update_inventory
from reporting import generate_report

from logging_config import logger
from access_control import require_access

app = Flask(__name__)
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

# Initialize rate limiter with global 200 req/hour
limiter = init_limiter(app)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f5f5f5;
            color: #171717;
            -webkit-font-smoothing: antialiased;
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
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            transform: translateY(-1px);
        }
        .card-icon {
            font-size: 28px;
            margin-bottom: 16px;
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
            line-height: 1.6;
            margin-bottom: 24px;
            font-weight: 400;
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
        }
        .card-btn:hover {
            background: #262626;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
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
        .loading-text {
            font-size: 14px;
            color: #737373;
        }
        
        /* Status */
        .success { color: #16a34a; font-weight: 500; }
        .error { color: #dc2626; font-weight: 500; }
        
        /* Toast Notifications */
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 14px 20px;
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
            font-weight: 500;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            animation: slideIn 0.3s ease;
            max-width: 400px;
        }
        .toast-success { background: #16a34a; }
        .toast-error { background: #dc2626; }
        .toast-info { background: #3b82f6; }
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .container { padding: 32px 16px; }
            .page-title { font-size: 24px; }
            .cards-grid { grid-template-columns: 1fr; }
            .banner { flex-direction: column; gap: 16px; text-align: center; }
            .header-nav { flex-wrap: wrap; gap: 4px; }
            .nav-btn { font-size: 13px; padding: 6px 12px; }
            .toast { right: 10px; left: 10px; max-width: calc(100% - 20px); }
        }
        
        @media (max-width: 480px) {
            .page-title { font-size: 20px; }
            .card { padding: 20px; }
            .card-title { font-size: 18px; }
        }
    </style>

    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-RBBQ4X7FJ3"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', 'G-RBBQ4X7FJ3');
    </script>
    </head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="logo">Employee Suite v1</div>
            <div class="header-nav">
                <a href="{{ url_for('shopify.shopify_settings') }}" class="nav-btn">Settings</a>
                <a href="{{ url_for('billing.subscribe') }}" class="nav-btn nav-btn-primary">Subscribe</a>
                <a href="/logout" class="nav-btn">Logout</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="page-title">Dashboard</div>
        <div class="page-subtitle">Manage your Shopify store automation</div>
        
        {% if trial_active and not is_subscribed %}
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
                <h3>Connect Your Store</h3>
                <p>Connect Shopify to start automating</p>
            </div>
            <a href="{{ url_for('shopify.shopify_settings') }}" class="banner-action">Connect</a>
        </div>
        {% endif %}
        
        <div class="cards-grid">
            <div class="card">
                <div class="card-icon">📦</div>
                <div class="card-title">Orders</div>
                <div class="card-description">Process pending Shopify orders</div>
                <button class="card-btn" onclick="processOrders()">Process Orders</button>
            </div>
            
            <div class="card">
                <div class="card-icon">📊</div>
                <div class="card-title">Inventory</div>
                <div class="card-description">Check stock levels and alerts</div>
                <button class="card-btn" onclick="updateInventory()">Check Inventory</button>
            </div>
            
            <div class="card">
                <div class="card-icon">💰</div>
                <div class="card-title">Reports</div>
                <div class="card-description">View revenue analytics</div>
                <button class="card-btn" onclick="generateReport()">Generate Report</button>
            </div>
        </div>
        
        <div class="output-container">
            <div class="output-header">Results</div>
            <div id="output"></div>
        </div>
    </div>
    
    <script>
        (function() {
        'use strict';
        
        // Global error handler
        window.addEventListener('error', function(e) {
            console.error('JavaScript Error:', e.message, e.filename, e.lineno);
        });
        
        // Test if JavaScript is working
        console.log('✅ JavaScript loaded');
        
        // Toast notification system
        function showToast(message, type) {
            type = type || 'success';
            var toast = document.createElement('div');
            toast.className = 'toast toast-' + type;
            toast.textContent = message;
            document.body.appendChild(toast);
            setTimeout(function() {
                toast.style.animation = 'slideIn 0.3s ease reverse';
                setTimeout(function() { toast.remove(); }, 300);
            }, 3000);
        }
        
        function showLoading() {
            var output = document.getElementById('output');
            if (output) {
                output.innerHTML = "<div class=\"loading\"><div class=\"spinner\"></div><div class=\"loading-text\">Processing...</div></div>";
            }
        }
        
        function processOrders() {
            console.log('processOrders called');
            showLoading();
            fetch('/api/process_orders')
                .then(function(r) {
                    if (!r.ok) throw new Error('HTTP ' + r.status + ': ' + r.statusText);
                    return r.json();
                })
                .then(function(d) {
                    var output = document.getElementById('output');
                    if (output) {
                        var c = d.success ? 'success' : 'error';
                        var symbol = d.success ? '✓' : '✗';
                        var status = d.success ? 'Success' : 'Error';
                        var msg = d.message || d.error || 'Unknown error';
                        output.innerHTML = "<h3 class=\"" + c + "\">" + symbol + " " + status + "</h3><p style=\"margin-top: 12px;\">" + msg + "</p>";
                    }
                    if (d.success) showToast('Orders processed successfully!', 'success');
                    else showToast('Failed to process orders', 'error');
                })
                .catch(function(error) {
                    var output = document.getElementById('output');
                    if (output) {
                        output.innerHTML = "<h3 class=\"error\">✗ Network Error</h3><p style=\"margin-top: 12px;\">Failed to process orders. Please check your connection and try again.</p><p style=\"margin-top: 8px; font-size: 12px; color: #737373;\">" + error.message + "</p>";
                    }
                    showToast('Network error. Please try again.', 'error');
                });
        }
        
        function updateInventory() {
            console.log('updateInventory called');
            showLoading();
            fetch('/api/update_inventory')
                .then(function(r) {
                    if (!r.ok) throw new Error('HTTP ' + r.status + ': ' + r.statusText);
                    return r.json();
                })
                .then(function(d) {
                    var output = document.getElementById('output');
                    if (output) {
                        var c = d.success ? 'success' : 'error';
                        var symbol = d.success ? '✓' : '✗';
                        var status = d.success ? 'Success' : 'Error';
                        var msg = d.message || d.error || 'Unknown error';
                        output.innerHTML = "<h3 class=\"" + c + "\">" + symbol + " " + status + "</h3><p style=\"margin-top: 12px; white-space: pre-wrap;\">" + msg + "</p>";
                    }
                    if (d.success) showToast('Inventory updated successfully!', 'success');
                    else showToast('Failed to update inventory', 'error');
                })
                .catch(function(error) {
                    var output = document.getElementById('output');
                    if (output) {
                        output.innerHTML = "<h3 class=\"error\">✗ Network Error</h3><p style=\"margin-top: 12px;\">Failed to update inventory. Please check your connection and try again.</p><p style=\"margin-top: 8px; font-size: 12px; color: #737373;\">" + error.message + "</p>";
                    }
                    showToast('Network error. Please try again.', 'error');
                });
        }
        
        function generateReport() {
            console.log('generateReport called');
            showLoading();
            fetch('/api/generate_report')
                .then(function(r) {
                    if (!r.ok) throw new Error('HTTP ' + r.status + ': ' + r.statusText);
                    return r.text();
                })
                .then(function(html) {
                    var output = document.getElementById('output');
                    if (output) {
                        output.innerHTML = html;
                    }
                    showToast('Report generated successfully!', 'success');
                })
                .catch(function(error) {
                    var output = document.getElementById('output');
                    if (output) {
                        output.innerHTML = "<h3 class=\"error\">✗ Network Error</h3><p style=\"margin-top: 12px;\">Failed to generate report. Please check your connection and try again.</p><p style=\"margin-top: 8px; font-size: 12px; color: #737373;\">" + error.message + "</p>";
                    }
                    showToast('Network error. Please try again.', 'error');
                });
        }
        
        function exportReport() {
            if (!window.reportData) {
                showToast('No report data available. Please generate a report first.', 'error');
                return;
            }
            
            var data = window.reportData;
            var csv = 'Revenue Report\n';
            csv += 'Total Revenue,' + data.totalRevenue.toFixed(2) + '\n';
            csv += 'Total Orders,' + data.totalOrders + '\n';
            csv += 'Average Order Value,' + (data.averageOrderValue || 0).toFixed(2) + '\n';
            csv += 'Total Items Sold,' + (data.totalItems || 0) + '\n';
            csv += 'Generated,' + data.timestamp + '\n\n';
            csv += 'Product,Revenue,Percentage\n';
            
            for (var i = 0; i < data.products.length; i++) {
                var product = data.products[i][0];
                var revenue = data.products[i][1];
                var percentage = ((revenue / data.totalRevenue) * 100).toFixed(1);
                csv += '"' + product + '",' + revenue.toFixed(2) + ',' + percentage + '%\n';
            }
            
            var blob = new Blob([csv], { type: 'text/csv' });
            var url = window.URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            var dateStr = new Date().toISOString().split('T')[0];
            a.download = 'revenue-report-' + dateStr + '.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            showToast('Report exported successfully!', 'success');
        }
        
        // Make functions globally accessible IMMEDIATELY
        window.processOrders = processOrders;
        window.updateInventory = updateInventory;
        window.generateReport = generateReport;
        window.exportReport = exportReport;
        
        // Verify functions are accessible
        console.log('✅ Functions defined:', typeof processOrders, typeof updateInventory, typeof generateReport);
        
        // Attach event listeners when DOM is ready
        function initButtons() {
            console.log('✅ DOM ready, initializing buttons');
            var buttons = document.querySelectorAll('.card-btn');
            console.log('✅ Buttons found:', buttons.length);
            
            // Attach click handlers directly as backup
            if (buttons.length >= 3) {
                buttons[0].addEventListener('click', function(e) {
                    e.preventDefault();
                    console.log('Button 1 clicked via addEventListener');
                    if (typeof processOrders === 'function') {
                        processOrders();
                    } else {
                        console.error('processOrders is not a function!');
                    }
                });
                buttons[1].addEventListener('click', function(e) {
                    e.preventDefault();
                    console.log('Button 2 clicked via addEventListener');
                    if (typeof updateInventory === 'function') {
                        updateInventory();
                    } else {
                        console.error('updateInventory is not a function!');
                    }
                });
                buttons[2].addEventListener('click', function(e) {
                    e.preventDefault();
                    console.log('Button 3 clicked via addEventListener');
                    if (typeof generateReport === 'function') {
                        generateReport();
                    } else {
                        console.error('generateReport is not a function!');
                    }
                });
                console.log('✅ Event listeners attached to all buttons');
            }
        }
        
        // Initialize buttons when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initButtons);
        } else {
            initButtons();
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + 1, 2, 3 for quick actions
            if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey) {
                if (e.key === '1') {
                    e.preventDefault();
                    processOrders();
                } else if (e.key === '2') {
                    e.preventDefault();
                    updateInventory();
                } else if (e.key === '3') {
                    e.preventDefault();
                    generateReport();
                }
            }
        });
        
        // Performance: Preload fonts
        if ('fonts' in document) {
            document.fonts.ready.then(function() {
                console.log('Fonts loaded');
            });
        }
        
        })(); // End IIFE - all functions now in global scope via window
    </script>

    <footer style="margin-top: 60px; padding: 24px; border-top: 1px solid #e5e5e5; text-align: center; background: #fff;">
        <div style="max-width: 1200px; margin: 0 auto; display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; font-size: 14px;">
            <a href="/faq" style="color: #525252; text-decoration: none; font-weight: 500;">FAQ</a>
            <span style="color: #d4d4d4;">|</span>
            <a href="/privacy" style="color: #525252; text-decoration: none; font-weight: 500;">Privacy Policy</a>
            <span style="color: #d4d4d4;">|</span>
            <a href="/terms" style="color: #525252; text-decoration: none; font-weight: 500;">Terms of Service</a>
            <span style="color: #d4d4d4;">|</span>
            <span style="color: #737373;">© 2025 Employee Suite</span>
        </div>
    </footer>
    <script src="/static/js/dashboard-fix.js"></script>
</body>
</html>
"""

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('auth.login'))

@app.route('/dashboard')
@login_required
@require_access
def dashboard():
    if not current_user.has_access():
        return redirect(url_for('billing.subscribe'))
    
    trial_active = current_user.is_trial_active()
    days_left = (current_user.trial_ends_at - datetime.utcnow()).days if trial_active else 0
    
    # Check if user has connected Shopify
    from models import ShopifyStore
    has_shopify = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first() is not None
    
    return render_template_string(DASHBOARD_HTML, trial_active=trial_active, days_left=days_left, is_subscribed=current_user.is_subscribed, has_shopify=has_shopify)


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

@app.route('/health')
def health():
    """Health check endpoint for monitoring"""
    try:
        # Quick DB connectivity check
        db.session.execute(db.text('SELECT 1'))
        return jsonify({"status": "healthy", "service": "Employee Suite", "version": "2.0", "database": "connected"}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/api/process_orders', methods=['GET', 'POST'])
@login_required
def api_process_orders():
    try:
        result = process_orders()
        if isinstance(result, dict):
            return jsonify(result)
        else:
            return jsonify({"message": str(result), "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/update_inventory', methods=['GET', 'POST'])
@login_required
def api_update_inventory():
    try:
        result = update_inventory()
        if isinstance(result, dict) and result.get("success"):
            return jsonify(result)
        else:
            return jsonify({"success": False, "error": str(result)})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/generate_report', methods=['GET', 'POST'])
@login_required
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
            try:
                # Check if reset_token column exists
                result = db.session.execute(db.text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='users' AND column_name='reset_token'
                """))
                if not result.fetchone():
                    logger.info("Adding reset_token columns to users table...")
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
                        # Column might already exist (race condition or already added)
                        if "already exists" in str(alter_error).lower() or "duplicate" in str(alter_error).lower():
                            logger.info("✅ reset_token columns already exist")
                        else:
                            logger.warning(f"Could not add reset_token columns: {alter_error}")
                        db.session.rollback()
                else:
                    logger.info("✅ reset_token columns already exist")
            except Exception as e:
                # If check fails, try to add columns anyway (might work)
                logger.warning(f"Could not check for reset_token columns: {e}")
            logger.info("Database tables initialized/verified")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")

# Run on import (for Render/Gunicorn)
init_db()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
