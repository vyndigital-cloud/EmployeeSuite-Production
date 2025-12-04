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

# Initialize rate limiter with global limits
limiter = init_limiter(app)

# Exempt specific routes from rate limiting (health checks, webhooks)
limiter.exempt(health)
limiter.exempt(stripe_webhook)

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
        
        /* Responsive */
        @media (max-width: 768px) {
            .container { padding: 32px 16px; }
            .page-title { font-size: 24px; }
            .cards-grid { grid-template-columns: 1fr; }
            .banner { flex-direction: column; gap: 16px; text-align: center; }
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
                .then(r => r.json())
                .then(d => {
                    const c = d.success ? 'success' : 'error';
                    document.getElementById('output').innerHTML = `
                        <h3 class="${c}">${d.success ? '✓' : '✗'} ${d.success ? 'Success' : 'Error'}</h3>
                        <p style="margin-top: 12px;">${d.message || d.error}</p>
                    `;
                });
        }
        
        function updateInventory() {
            showLoading();
            fetch('/api/update_inventory')
                .then(r => r.json())
                .then(d => {
                    const c = d.success ? 'success' : 'error';
                    document.getElementById('output').innerHTML = `
                        <h3 class="${c}">${d.success ? '✓' : '✗'} ${d.success ? 'Success' : 'Error'}</h3>
                        <p style="margin-top: 12px; white-space: pre-wrap;">${d.message || d.error}</p>
                    `;
                });
        }
        
        function generateReport() {
            showLoading();
            fetch('/api/generate_report')
                .then(r => r.text())
                .then(html => {
                    document.getElementById('output').innerHTML = html;
                });
        }
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
    return jsonify({"status": "healthy", "service": "Employee Suite", "version": "2.0"})

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
    try:
        from reporting import generate_report_html
        data = generate_report()
        if data.get('error') and data['error'] is not None:
            return f"<h3 class='error'>❌ Error: {data['error']}</h3>", 500
        
        html = generate_report_html(data)
        return html
    except Exception as e:
        return f"<h3 class='error'>❌ Error: {str(e)}</h3>", 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found", "status": 404}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error", "status": 500}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
