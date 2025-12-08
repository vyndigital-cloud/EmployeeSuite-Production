from flask import Blueprint, render_template_string, request, redirect, url_for, session
from models import db, User, ShopifyStore
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

ADMIN_LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #fafafa;
            color: #171717;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 24px;
        }
        .login-container { width: 100%; max-width: 400px; }
        .logo { text-align: center; font-size: 24px; font-weight: 700; color: #171717; margin-bottom: 32px; }
        .card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 32px; }
        .card-title { font-size: 20px; font-weight: 600; color: #171717; margin-bottom: 24px; }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; font-size: 14px; font-weight: 500; color: #171717; margin-bottom: 8px; }
        .form-input { width: 100%; padding: 12px; border: 1px solid #e5e5e5; border-radius: 6px; font-size: 14px; font-family: inherit; }
        .form-input:focus { outline: none; border-color: #171717; }
        .btn { width: 100%; padding: 12px; background: #171717; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; }
        .btn:hover { background: #262626; }
        .banner-error { background: #fef2f2; border: 1px solid #fecaca; border-left: 3px solid #dc2626; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 14px; color: #991b1b; }
        
        /* Mobile Responsive */
        @media (max-width: 768px) {
            body { padding: 16px; }
            .card { padding: 24px; }
            .logo { font-size: 20px; }
        }
        @media (max-width: 480px) {
            .card { padding: 20px; }
            .card-title { font-size: 18px; }
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">🔒 Admin</div>
        <div class="card">
            <h1 class="card-title">Admin Login</h1>
            {% if error %}
            <div class="banner-error">{{ error }}</div>
            {% endif %}
            <form method="POST">
                <div class="form-group">
                    <label class="form-label">Password</label>
                    <input type="password" name="password" class="form-input" required autofocus>
                </div>
                <button type="submit" class="btn">Login</button>
            </form>
        </div>
    </div>
</body>
</html>
'''

ADMIN_DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #fafafa;
            color: #171717;
        }
        .header { background: #fff; border-bottom: 1px solid #e5e5e5; }
        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 24px;
            height: 64px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo { font-size: 18px; font-weight: 600; color: #171717; }
        .nav-btn { padding: 8px 14px; border-radius: 6px; font-size: 14px; font-weight: 500; text-decoration: none; background: #171717; color: #fff; }
        .nav-btn:hover { background: #262626; }
        .container { max-width: 1400px; margin: 0 auto; padding: 48px 24px; }
        .page-title { font-size: 32px; font-weight: 700; color: #171717; margin-bottom: 8px; }
        .page-subtitle { font-size: 16px; color: #737373; margin-bottom: 32px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 40px; }
        .stat-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 24px; }
        .stat-label { font-size: 13px; color: #737373; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
        .stat-value { font-size: 32px; font-weight: 700; color: #171717; }
        .table-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; overflow: hidden; }
        .table-header { padding: 20px 24px; border-bottom: 1px solid #e5e5e5; font-size: 16px; font-weight: 600; color: #171717; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 16px 24px; font-size: 13px; font-weight: 600; color: #737373; background: #fafafa; text-transform: uppercase; letter-spacing: 0.5px; }
        td { padding: 16px 24px; font-size: 14px; color: #171717; border-bottom: 1px solid #f5f5f5; }
        .badge { display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .badge-success { background: #dcfce7; color: #166534; }
        .badge-warning { background: #fef3c7; color: #92400e; }
        .badge-error { background: #fee2e2; color: #991b1b; }
        
        /* Mobile Responsive */
        @media (max-width: 768px) {
            .container { padding: 32px 16px; }
            .page-title { font-size: 26px; }
            .page-subtitle { font-size: 15px; }
            .stats-grid { grid-template-columns: 1fr; }
            .header-content { padding: 0 16px; }
            .table-card { overflow-x: auto; }
            table { min-width: 600px; }
        }
        @media (max-width: 480px) {
            .page-title { font-size: 24px; }
            .stat-card { padding: 20px; }
            .stat-value { font-size: 28px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="logo">🔒 Admin Dashboard</div>
            <a href="{{ url_for('admin.logout') }}" class="nav-btn">Logout</a>
        </div>
    </div>
    
    <div class="container">
        <h1 class="page-title">Dashboard</h1>
        <p class="page-subtitle">System overview and user management</p>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Users</div>
                <div class="stat-value">{{ total_users }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Subscribed</div>
                <div class="stat-value">{{ subscribed_users }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Trial Users</div>
                <div class="stat-value">{{ trial_users }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Connected Stores</div>
                <div class="stat-value">{{ total_stores }}</div>
            </div>
        </div>
        
        <div class="table-card">
            <div class="table-header">All Users</div>
            <table>
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Action</th>
                        <th>Status</th>
                        <th>Trial Ends</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
                    {% for user in users %}
                    <tr>
                        <td>{{ user.email }}</td>
                        <td>
                            <form method="POST" action="{{ url_for('admin.delete_user', user_id=user.id) }}" style="display:inline;" onsubmit="return confirm('Delete {{ user.email }}?')">
                                <button type="submit" style="background:#dc2626;color:#fff;border:none;padding:4px 10px;border-radius:4px;font-size:12px;cursor:pointer;font-weight:600;">Delete</button>
                            </form>
                        </td>
                        <td>
                            {% if user.is_subscribed %}
                            <span class="badge badge-success">Subscribed</span>
                            {% elif user.is_trial_active() %}
                            <span class="badge badge-warning">Trial</span>
                            {% else %}
                            <span class="badge badge-error">Expired</span>
                            {% endif %}
                        </td>
                        <td>{{ user.trial_ends_at.strftime('%Y-%m-%d %H:%M') if user.trial_ends_at else 'N/A' }}</td>
                        <td>{{ user.created_at.strftime('%Y-%m-%d') }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
'''

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        import os
        password = request.form.get('password')
        if password == os.getenv('ADMIN_PASSWORD'):
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        return render_template_string(ADMIN_LOGIN_HTML, error="Invalid password")
    return render_template_string(ADMIN_LOGIN_HTML)

@admin_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))

@admin_bp.route('/')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.login'))
    
    users = User.query.all()
    total_users = len(users)
    subscribed_users = len([u for u in users if u.is_subscribed])
    trial_users = len([u for u in users if u.is_trial_active()])
    total_stores = ShopifyStore.query.filter_by(is_active=True).count()
    
    return render_template_string(
        ADMIN_DASHBOARD_HTML,
        users=users,
        total_users=total_users,
        subscribed_users=subscribed_users,
        trial_users=trial_users,
        total_stores=total_stores
    )

@admin_bp.route('/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """Delete a user and their associated data"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.login'))
    
    try:
        user = User.query.get(user_id)
        if user:
            # Delete associated stores
            ShopifyStore.query.filter_by(user_id=user.id).delete()
            # Delete user
            email = user.email
            db.session.delete(user)
            db.session.commit()
            return redirect(url_for('admin.dashboard') + f'?deleted={email}')
        else:
            return redirect(url_for('admin.dashboard') + '?error=User not found')
    except Exception as e:
        return redirect(url_for('admin.dashboard') + f'?error={str(e)}')

