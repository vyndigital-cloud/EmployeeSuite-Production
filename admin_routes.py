from flask import Blueprint, render_template_string, request, redirect, url_for, session
from models import db, User, ShopifyStore
from datetime import datetime, timedelta
import os

admin_bp = Blueprint('admin', __name__)

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

ADMIN_LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login</title>
        <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #fafafa;
            color: #171717;
            -webkit-font-smoothing: antialiased;
        }
        .header {
            background: #fff;
            border-bottom: 1px solid #e5e5e5;
        }
        .header-content {
            max-width: 1400px;
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
        .nav-btn {
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            background: #171717;
            color: #fff;
        }
        .nav-btn:hover {
            background: #262626;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 48px 24px;
        }
        .page-title {
            font-size: 32px;
            font-weight: 700;
            color: #171717;
            margin-bottom: 8px;
        }
        .page-subtitle {
            font-size: 16px;
            color: #737373;
            margin-bottom: 32px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 12px;
            padding: 24px;
        }
        .stat-label {
            font-size: 13px;
            color: #737373;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .stat-value {
            font-size: 32px;
            font-weight: 700;
            color: #171717;
        }
        .table-card {
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 12px;
            overflow: hidden;
        }
        .table-header {
            padding: 20px 24px;
            border-bottom: 1px solid #e5e5e5;
            font-size: 16px;
            font-weight: 600;
            color: #171717;
        }
        .table-container {
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            text-align: left;
            padding: 16px 24px;
            font-size: 13px;
            font-weight: 600;
            color: #737373;
            background: #fafafa;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        td {
            padding: 16px 24px;
            font-size: 14px;
            color: #171717;
            border-bottom: 1px solid #f5f5f5;
        }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-success {
            background: #dcfce7;
            color: #166534;
        }
        .badge-warning {
            background: #fef3c7;
            color: #92400e;
        }
        .badge-error {
            background: #fee2e2;
            color: #991b1b;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Admin Login</h1>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <input type="password" name="password" placeholder="Admin Password" required autofocus>
            <button type="submit" class="btn">Login</button>
        </form>
    </div>
</body>
</html>
"""

ADMIN_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto; background: #f8f9fa; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: white; padding: 20px 30px; border-radius: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header h1 { color: #667eea; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-card h3 { color: #667eea; font-size: 2.5em; margin-bottom: 10px; }
        .stat-card p { color: #666; font-size: 0.9em; }
        .users-table { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow-x: auto; }
        .users-table h2 { color: #333; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; min-width: 600px; }
        th { background: #f8f9fa; padding: 12px; text-align: left; color: #333; font-weight: 600; border-bottom: 2px solid #dee2e6; }
        td { padding: 12px; border-bottom: 1px solid #eee; color: #666; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .badge-trial { background: #fff3cd; color: #856404; }
        .badge-subscribed { background: #d4edda; color: #155724; }
        .badge-expired { background: #f8d7da; color: #721c24; }
        .logout-btn { background: #dc3545; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; border: none; cursor: pointer; }
        .logout-btn:hover { background: #c82333; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Admin Dashboard</h1>
            <a href="{{ url_for('admin.logout') }}" class="logout-btn">Logout</a>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>{{ total_users }}</h3>
                <p>👥 Total Users</p>
            </div>
            <div class="stat-card">
                <h3>{{ subscribers }}</h3>
                <p>✅ Active Subscribers</p>
            </div>
            <div class="stat-card">
                <h3>{{ trial_users }}</h3>
                <p>⏰ Trial Users</p>
            </div>
            <div class="stat-card">
                <h3>${{ "{:,.0f}".format(mrr) }}</h3>
                <p>💰 Monthly Recurring Revenue</p>
            </div>
            <div class="stat-card">
                <h3>${{ "{:,.0f}".format(setup_revenue) }}</h3>
                <p>🎉 Setup Fee Revenue</p>
            </div>
            <div class="stat-card">
                <h3>${{ "{:,.0f}".format(total_revenue) }}</h3>
                <p>💎 Total Revenue</p>
            </div>
        </div>
        
        <div class="users-table">
            <h2>Recent Users (Last 50)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Status</th>
                        <th>Trial Ends</th>
                        <th>Joined</th>
                        <th>Shopify</th>
                        <th>Stripe ID</th>
                    </tr>
                </thead>
                <tbody>
                    {% for user in users %}
                    <tr>
                        <td>{{ user.email }}</td>
                        <td>
                            {% if user.is_subscribed %}
                            <span class="badge badge-subscribed">💳 Subscribed</span>
                            {% elif user.trial_active %}
                            <span class="badge badge-trial">⏰ Trial</span>
                            {% else %}
                            <span class="badge badge-expired">❌ Expired</span>
                            {% endif %}
                        </td>
                        <td>{{ user.trial_ends_at.strftime('%b %d, %Y') if user.trial_ends_at else 'N/A' }}</td>
                        <td>{{ user.created_at.strftime('%b %d, %Y') }}</td>
                        <td>{{ '✅ Connected' if user.has_store else '❌ Not connected' }}</td>
                        <td>{{ user.stripe_customer_id[:20] + '...' if user.stripe_customer_id else 'N/A' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        return render_template_string(ADMIN_LOGIN_HTML, error="Invalid password")
    return render_template_string(ADMIN_LOGIN_HTML)

@admin_bp.route('/admin')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.login'))
    
    total_users = User.query.count()
    subscribers = User.query.filter_by(is_subscribed=True).count()
    trial_users = User.query.filter(User.trial_ends_at > datetime.utcnow(), User.is_subscribed == False).count()
    
    mrr = subscribers * 500
    setup_revenue = subscribers * 1000
    total_revenue = setup_revenue + mrr
    
    users = User.query.order_by(User.created_at.desc()).limit(50).all()
    
    for user in users:
        user.trial_active = user.is_trial_active()
        user.has_store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first() is not None
    
    return render_template_string(
        ADMIN_DASHBOARD_HTML,
        total_users=total_users,
        subscribers=subscribers,
        trial_users=trial_users,
        mrr=mrr,
        setup_revenue=setup_revenue,
        total_revenue=total_revenue,
        users=users
    )

@admin_bp.route('/admin/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))
