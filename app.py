from flask import Flask, jsonify, render_template_string, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from flask_bcrypt import Bcrypt
import os
from datetime import datetime

from models import db, User, ShopifyStore
from auth import auth_bp, bcrypt as auth_bcrypt
from shopify_routes import shopify_bp
from billing import billing_bp
from admin_routes import admin_bp
from legal_routes import legal_bp
from order_processing import process_orders
from inventory import update_inventory
from reporting import generate_report

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///employeesuite.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
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

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif; 
            background: #f5f7fa; 
            min-height: 100vh; 
        }
        
        /* Header */
        .header { 
            background: #fff; 
            border-bottom: 1px solid #e1e8ed;
            padding: 0 40px;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 70px;
        }
        .logo { 
            font-size: 24px; 
            font-weight: 700; 
            color: #667eea;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .user-badge {
            background: #f5f7fa;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            color: #666;
            font-weight: 500;
        }
        .btn-header {
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            border: none;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-subscribe { background: #ffc107; color: #000; }
        .btn-subscribe:hover { background: #ffb300; transform: translateY(-1px); }
        .btn-settings { background: #28a745; color: white; }
        .btn-settings:hover { background: #218838; transform: translateY(-1px); }
        .btn-logout { background: #f5f7fa; color: #666; border: 1px solid #e1e8ed; }
        .btn-logout:hover { background: #e1e8ed; }
        
        /* Container */
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            padding: 40px 40px 80px;
        }
        
        /* Trial Banner */
        .trial-banner {
            background: linear-gradient(135deg, #fff3cd 0%, #ffe69c 100%);
            border-left: 4px solid #ffc107;
            padding: 20px 24px;
            border-radius: 8px;
            margin-bottom: 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 8px rgba(255, 193, 7, 0.1);
        }
        .trial-banner h3 { 
            color: #856404; 
            font-size: 16px; 
            font-weight: 600;
            margin-bottom: 4px;
        }
        .trial-banner p { 
            color: #856404; 
            font-size: 14px;
        }
        .trial-banner .days-left {
            font-size: 32px;
            font-weight: 700;
            color: #d63384;
        }
        
        /* Setup Banner */
        .setup-banner {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 24px;
            border-radius: 12px;
            margin-bottom: 32px;
            color: white;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }
        .setup-banner h3 { 
            font-size: 18px; 
            margin-bottom: 8px;
            font-weight: 600;
        }
        .setup-banner p { 
            font-size: 14px; 
            opacity: 0.95;
            line-height: 1.6;
        }
        .setup-banner .btn-setup {
            background: white;
            color: #667eea;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: 600;
            text-decoration: none;
            display: inline-block;
            margin-top: 12px;
            font-size: 14px;
        }
        .setup-banner .btn-setup:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        /* Stats Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: white;
            padding: 24px;
            border-radius: 12px;
            border: 1px solid #e1e8ed;
            transition: all 0.2s;
        }
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        .stat-icon {
            font-size: 32px;
            margin-bottom: 12px;
        }
        .stat-label {
            font-size: 13px;
            color: #8899a6;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .stat-value {
            font-size: 28px;
            font-weight: 700;
            color: #14171a;
        }
        
        /* Action Cards */
        .actions-section h2 {
            font-size: 20px;
            color: #14171a;
            margin-bottom: 20px;
            font-weight: 700;
        }
        .actions-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }
        .action-card {
            background: white;
            border-radius: 12px;
            border: 1px solid #e1e8ed;
            overflow: hidden;
            transition: all 0.2s;
        }
        .action-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.1);
            border-color: #667eea;
        }
        .action-header {
            padding: 24px;
            background: linear-gradient(135deg, #f5f7fa 0%, #fff 100%);
            border-bottom: 1px solid #e1e8ed;
        }
        .action-icon {
            font-size: 40px;
            margin-bottom: 12px;
        }
        .action-title {
            font-size: 20px;
            font-weight: 700;
            color: #14171a;
            margin-bottom: 8px;
        }
        .action-description {
            font-size: 14px;
            color: #657786;
            line-height: 1.5;
        }
        .action-body {
            padding: 24px;
        }
        .action-btn {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 24px;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
        }
        .action-btn:active {
            transform: translateY(0);
        }
        
        /* Output Panel */
        .output-panel {
            background: white;
            border-radius: 12px;
            border: 1px solid #e1e8ed;
            overflow: hidden;
        }
        .output-header {
            padding: 20px 24px;
            background: #f5f7fa;
            border-bottom: 1px solid #e1e8ed;
            font-weight: 600;
            color: #14171a;
            font-size: 15px;
        }
        #output {
            padding: 24px;
            min-height: 300px;
            max-height: 600px;
            overflow-y: auto;
            white-space: pre-wrap;
            font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.6;
            color: #14171a;
        }
        #output:empty:before {
            content: 'Click any action above to see results...';
            color: #8899a6;
            font-style: italic;
        }
        
        /* Loading */
        .loading-container {
            text-align: center;
            padding: 60px 20px;
        }
        .loading-spinner {
            display: inline-block;
            width: 40px;
            height: 40px;
            border: 4px solid #f5f7fa;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .loading-text {
            margin-top: 16px;
            color: #8899a6;
            font-size: 14px;
        }
        
        /* Success/Error States */
        .success { color: #28a745; font-weight: 600; }
        .error { color: #dc3545; font-weight: 600; }
        
        /* Responsive */
        @media (max-width: 768px) {
            .header { padding: 0 20px; }
            .container { padding: 20px; }
            .header-content { height: 60px; }
            .logo { font-size: 20px; }
            .stats-grid { grid-template-columns: 1fr; }
            .actions-grid { grid-template-columns: 1fr; }
            .trial-banner { flex-direction: column; text-align: center; gap: 16px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="logo">
                <span>🚀</span>
                <span>Employee Suite</span>
            </div>
            <div class="header-actions">
                <span class="user-badge">{{ current_user.email }}</span>
                <a href="{{ url_for('billing.subscribe') }}" class="btn-header btn-subscribe">💳 Subscribe</a>
                <a href="{{ url_for('shopify.shopify_settings') }}" class="btn-header btn-settings">⚙️ Settings</a>
                <a href="{{ url_for('auth.logout') }}" class="btn-header btn-logout">Logout</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        {% if trial_active and not is_subscribed %}
        <div class="trial-banner">
            <div>
                <h3>⏰ Free Trial Active</h3>
                <p>Your trial ends in <strong>{{ days_left }} day{{ 's' if days_left != 1 else '' }}</strong>. Subscribe to continue without interruption.</p>
            </div>
            <div class="days-left">{{ days_left }}</div>
        </div>
        {% endif %}
        
        {% if not has_shopify %}
        <div class="setup-banner">
            <h3>⚡ Quick Setup Required</h3>
            <p>Connect your Shopify store to start automating inventory management. Takes less than 2 minutes.</p>
            <a href="{{ url_for('shopify.shopify_settings') }}" class="btn-setup">Connect Shopify Store →</a>
        </div>
        {% endif %}
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">📦</div>
                <div class="stat-label">Status</div>
                <div class="stat-value">{{ 'Active' if has_shopify else 'Setup' }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">⚡</div>
                <div class="stat-label">Automation</div>
                <div class="stat-value">{{ 'On' if has_shopify else 'Off' }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">💎</div>
                <div class="stat-label">Plan</div>
                <div class="stat-value">{{ 'Pro' if is_subscribed else 'Trial' }}</div>
            </div>
        </div>
        
        <div class="actions-section">
            <h2>Quick Actions</h2>
            <div class="actions-grid">
                <div class="action-card">
                    <div class="action-header">
                        <div class="action-icon">📦</div>
                        <div class="action-title">Process Orders</div>
                        <div class="action-description">View and process pending Shopify orders in real-time</div>
                    </div>
                    <div class="action-body">
                        <button class="action-btn" onclick="processOrders()">Process Orders</button>
                    </div>
                </div>
                
                <div class="action-card">
                    <div class="action-header">
                        <div class="action-icon">📊</div>
                        <div class="action-title">Check Inventory</div>
                        <div class="action-description">Monitor stock levels and receive low-stock alerts</div>
                    </div>
                    <div class="action-body">
                        <button class="action-btn" onclick="updateInventory()">Check Inventory</button>
                    </div>
                </div>
                
                <div class="action-card">
                    <div class="action-header">
                        <div class="action-icon">💰</div>
                        <div class="action-title">Revenue Reports</div>
                        <div class="action-description">Analyze product performance and revenue metrics</div>
                    </div>
                    <div class="action-body">
                        <button class="action-btn" onclick="generateReport()">Generate Report</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="output-panel">
            <div class="output-header">Results</div>
            <div id="output"></div>
        </div>
    </div>
    
    <script>
        function showLoading() {
            document.getElementById('output').innerHTML = `
                <div class="loading-container">
                    <div class="loading-spinner"></div>
                    <div class="loading-text">Processing...</div>
                </div>
            `;
        }
        
        function processOrders() {
            showLoading();
            fetch('/api/process_orders')
                .then(response => response.json())
                .then(data => {
                    const msg = data.message || data.error;
                    const className = data.success ? 'success' : 'error';
                    document.getElementById('output').innerHTML = `
                        <h3 class="${className}">${data.success ? '✅' : '❌'} ${data.success ? 'Orders Processed' : 'Error'}</h3>
                        <p style="margin-top: 12px; font-size: 15px;">${msg}</p>
                    `;
                })
                .catch(error => {
                    document.getElementById('output').innerHTML = `
                        <h3 class="error">❌ Error</h3>
                        <p style="margin-top: 12px;">${error}</p>
                    `;
                });
        }
        
        function updateInventory() {
            showLoading();
            fetch('/api/update_inventory')
                .then(response => response.json())
                .then(data => {
                    const msg = data.message || data.error;
                    const className = data.success ? 'success' : 'error';
                    document.getElementById('output').innerHTML = `
                        <h3 class="${className}">${data.success ? '✅' : '❌'} ${data.success ? 'Inventory Updated' : 'Error'}</h3>
                        <p style="margin-top: 12px; font-size: 15px; white-space: pre-wrap;">${msg}</p>
                    `;
                })
                .catch(error => {
                    document.getElementById('output').innerHTML = `
                        <h3 class="error">❌ Error</h3>
                        <p style="margin-top: 12px;">${error}</p>
                    `;
                });
        }
        
        function generateReport() {
            showLoading();
            fetch('/api/generate_report')
                .then(response => response.text())
                .then(html => {
                    document.getElementById('output').innerHTML = html;
                })
                .catch(error => {
                    document.getElementById('output').innerHTML = `
                        <h3 class="error">❌ Error</h3>
                        <p style="margin-top: 12px;">${error}</p>
                    `;
                });
        }
    </script>
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

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "Employee Suite", "version": "2.0"})

@app.route('/api/process_orders', methods=['GET', 'POST'])
@login_required
def api_process_orders():
    try:
        result = process_orders()
        return jsonify({"message": result, "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/update_inventory', methods=['GET', 'POST'])
@login_required
def api_update_inventory():
    try:
        result = update_inventory()
        return jsonify({"message": result, "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/generate_report', methods=['GET', 'POST'])
@login_required
def api_generate_report():
    try:
        data = generate_report()
        if 'error' in data:
            return f"<h3 class='error'>❌ Error: {data['error']}</h3>", 500
        
        html = '<style>.report-item{padding:15px;border-bottom:1px solid #eee;display:flex;justify-content:space-between}.report-item strong{color:#667eea}.total{font-size:1.3em;color:#28a745;margin-top:20px;padding:20px;background:#f8f9fa;border-radius:8px;text-align:center}.stat{margin:10px 0}</style><h3 class="success">📊 Revenue Report</h3>'
        
        if len(data['products']) == 0:
            html += '<p style="text-align:center;color:#999;padding:40px;">No products found. Connect your Shopify store first.</p>'
        else:
            for product in data['products']:
                html += f'<div class="report-item"><strong>{product["name"]}</strong><span>Stock: {product["stock"]} | Revenue: {product["revenue"]}</span></div>'
        
        html += f'<div class="total">'
        html += f'<div class="stat">💰 Total Revenue: <strong>{data["total_revenue"]}</strong></div>'
        html += f'<div class="stat">📦 Total Products: <strong>{data["total_products"]}</strong></div>'
        if 'total_orders' in data:
            html += f'<div class="stat">🛍️ Total Orders: <strong>{data["total_orders"]}</strong></div>'
        html += f'</div>'
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
