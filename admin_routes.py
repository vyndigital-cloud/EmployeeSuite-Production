import os
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
            background: #f6f6f7;
            background-image: radial-gradient(circle at top right, rgba(0, 128, 96, 0.05), transparent 40%),
                              radial-gradient(circle at bottom left, rgba(0, 128, 96, 0.05), transparent 40%);
            color: #202223;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 24px;
        }
        .login-container { width: 100%; max-width: 400px; animation: fadeIn 0.5s ease-out; }
        .logo { 
            text-align: center; 
            margin-bottom: 24px; 
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            font-weight: 700;
            color: #008060;
            font-size: 20px;
        }
        .card { 
            background: #fff; 
            border: 1px solid #e1e3e5; 
            border-radius: 16px; 
            padding: 32px; 
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); 
        }
        .card-title { 
            font-size: 24px; 
            font-weight: 700; 
            color: #202223; 
            margin-bottom: 8px; 
            text-align: center;
        }
        .card-subtitle {
            text-align: center;
            color: #6d7175;
            font-size: 14px;
            margin-bottom: 32px;
        }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; font-size: 13px; font-weight: 600; color: #202223; margin-bottom: 8px; }
        .form-input { 
            width: 100%; 
            padding: 12px 16px; 
            border: 1px solid #dcdfe3; 
            border-radius: 8px; 
            font-size: 15px; 
            font-family: inherit; 
            background: #fff; 
            transition: all 0.2s; 
        }
        .form-input:focus { 
            outline: none; 
            border-color: #008060; 
            box-shadow: 0 0 0 1px #008060; 
        }
        .btn { 
            width: 100%; 
            padding: 12px; 
            background: #008060; 
            color: #fff; 
            border: none; 
            border-radius: 8px; 
            font-size: 15px; 
            font-weight: 600; 
            cursor: pointer; 
            transition: all 0.2s ease; 
            box-shadow: 0 2px 5px rgba(0, 128, 96, 0.2);
        }
        .btn:hover { 
            background: #006e52; 
            transform: translateY(-1px); 
            box-shadow: 0 4px 8px rgba(0, 128, 96, 0.3); 
        }
        .banner-error { 
            background: #fff4f4; 
            border: 1px solid #fecaca; 
            border-left: 3px solid #dc2626; 
            padding: 12px 16px; 
            border-radius: 8px; 
            margin-bottom: 24px; 
            font-size: 14px; 
            color: #b91c1c; 
            display: flex;
            align-items: center;
            gap: 8px;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <svg width="24" height="24" viewBox="0 0 256 256" fill="currentColor"><path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm0,192a88,88,0,1,1,88-88A88.1,88.1,0,0,1,128,216Zm-8-80V80a8,8,0,0,1,16,0v56a8,8,0,0,1-16,0Zm20,36a12,12,0,1,1-12-12A12,12,0,0,1,140,172Z"></path></svg>
            <span>Employee Suite</span>
        </div>
        <div class="card">
            <h1 class="card-title">Admin Access</h1>
            <p class="card-subtitle">Secure system login</p>
            {% if error %}
            <div class="banner-error">
                <svg width="16" height="16" viewBox="0 0 256 256" fill="currentColor"><path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm0,192a88,88,0,1,1,88-88A88.1,88.1,0,0,1,128,216Zm-8-80V80a8,8,0,0,1,16,0v56a8,8,0,0,1-16,0Zm20,36a12,12,0,1,1-12-12A12,12,0,0,1,140,172Z"></path></svg>
                {{ error }}
            </div>
            {% endif %}
            <form method="POST">
                <div class="form-group">
                    <label class="form-label">Password check</label>
                    <input type="password" name="password" class="form-input" placeholder="Enter admin key" required autofocus>
                </div>
                <button type="submit" class="btn">Authenticate</button>
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
            background: #f6f6f7;
            background-image: radial-gradient(circle at top right, rgba(0, 128, 96, 0.05), transparent 40%),
                              radial-gradient(circle at bottom left, rgba(0, 128, 96, 0.05), transparent 40%);
            color: #202223;
            min-height: 100vh;
        }
        .header { 
            background: rgba(255, 255, 255, 0.9); 
            backdrop-filter: blur(10px);
            border-bottom: 1px solid #e1e3e5; 
            position: sticky;
            top: 0;
            z-index: 50;
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
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .logo svg { color: #008060; }
        
        .nav-btn { 
            padding: 8px 16px; 
            border-radius: 8px; 
            font-size: 13px; 
            font-weight: 500; 
            text-decoration: none; 
            color: #6d7175; 
            border: 1px solid #e1e3e5;
            background: white;
            transition: all 0.2s ease; 
        }
        .nav-btn:hover { 
            border-color: #dcdfe3;
            background: #f6f6f7;
            color: #202223;
        }
        
        .container { max-width: 1200px; margin: 0 auto; padding: 40px 24px; }
        
        .page-header { margin-bottom: 32px; display: flex; justify-content: space-between; align-items: flex-end; }
        .page-title { font-size: 28px; font-weight: 700; color: #202223; margin-bottom: 4px; }
        .page-subtitle { font-size: 14px; color: #6d7175; }
        
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); 
            gap: 20px; 
            margin-bottom: 40px; 
        }
        .stat-card { 
            background: #fff; 
            border: 1px solid #e1e3e5; 
            border-radius: 12px; 
            padding: 24px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .stat-label { font-size: 12px; color: #6d7175; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
        .stat-value { font-size: 32px; font-weight: 700; color: #202223; letter-spacing: -0.5px; }
        .stat-highlight { color: #008060; }
        
        .table-card { 
            background: #fff; 
            border: 1px solid #e1e3e5; 
            border-radius: 12px; 
            overflow: hidden; 
            box-shadow: 0 4px 6px -2px rgba(0, 0, 0, 0.03); 
        }
        .table-header { 
            padding: 20px 24px; 
            border-bottom: 1px solid #e1e3e5; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
        }
        .table-title { font-size: 16px; font-weight: 600; color: #202223; }
        
        table { width: 100%; border-collapse: collapse; }
        th { 
            text-align: left; 
            padding: 12px 24px; 
            font-size: 12px; 
            font-weight: 600; 
            color: #6d7175; 
            background: #fcfcfc; 
            text-transform: uppercase; 
            letter-spacing: 0.5px; 
            border-bottom: 1px solid #e1e3e5;
        }
        td { padding: 16px 24px; font-size: 14px; color: #202223; border-bottom: 1px solid #f0f1f2; }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: #f9fafb; }
        
        .badge { display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; border: 1px solid transparent; gap: 4px; }
        .badge-success { background: #e3fcef; color: #008060; border-color: #bbf7d0; }
        .badge-warning { background: #fff7ed; color: #9a3412; border-color: #fed7aa; }
        .badge-error { background: #fef2f2; color: #b91c1c; border-color: #fecaca; }
        
        .btn-delete {
            background: white;
            color: #d72c0d;
            border: 1px solid #dcdfe3;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
        }
        .btn-delete:hover {
            background: #fff4f4;
            border-color: #fecaca;
            color: #d93535;
        }
        
        /* Mobile Responsive */
        @media (max-width: 768px) {
            .container { padding: 24px 16px; }
            .stats-grid { grid-template-columns: 1fr; }
            .table-card { overflow-x: auto; }
            table { min-width: 600px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="logo">
                <svg width="20" height="20" viewBox="0 0 256 256" fill="currentColor"><path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm0,192a88,88,0,1,1,88-88A88.1,88.1,0,0,1,128,216Zm-8-80V80a8,8,0,0,1,16,0v56a8,8,0,0,1-16,0Zm20,36a12,12,0,1,1-12-12A12,12,0,0,1,140,172Z"></path></svg>
                Employee Suite Admin
            </div>
            <a href="{{ url_for('admin.logout') }}" class="nav-btn">Logout</a>
        </div>
    </div>
    
    <div class="container">
        <div class="page-header">
            <div>
                <h1 class="page-title">Overview</h1>
                <p class="page-subtitle">Platform performance and user management</p>
            </div>
            <div>
                <!-- Optional Header Action -->
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Users</div>
                <div class="stat-value">{{ total_users }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Pro Subscribers</div>
                <div class="stat-value stat-highlight">{{ subscribed_users }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Active Trials</div>
                <div class="stat-value">{{ trial_users }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Connected Stores</div>
                <div class="stat-value">{{ total_stores }}</div>
            </div>
        </div>
        
        <div class="table-card">
            <div class="table-header">
                <div class="table-title">Registered Users</div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Subscription</th>
                        <th>Status</th>
                        <th>Trial Info</th>
                        <th>Joined</th>
                        <th style="text-align: right;">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for user in users %}
                    <tr>
                        <td style="font-weight: 500;">
                            {{ user.email }}
                            <div style="font-size: 11px; color: #6d7175; font-weight: 400; margin-top: 2px;">ID: {{ user.id }}</div>
                        </td>
                        <td>
                            {% if user.is_subscribed %}
                            <span class="badge badge-success">
                                <svg width="10" height="10" viewBox="0 0 256 256" fill="currentColor"><path d="M229.66,55.51a8,8,0,0,0-11.32.79L94.55,183.76,37.66,131a8,8,0,0,0-10.89,11.75l62.43,58a8,8,0,0,0,11.37-.53L230.45,66.84A8,8,0,0,0,229.66,55.51Z"></path></svg>
                                Pro Plan
                            </span>
                            {% else %}
                            <span style="color: #6d7175; font-size: 13px;">Free Plan</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if user.is_subscribed %}
                            <span class="badge badge-success">Active</span>
                            {% elif user.is_trial_active() %}
                            <span class="badge badge-warning">Trial</span>
                            {% else %}
                            <span class="badge badge-error">Expired</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if user.trial_ends_at %}
                                <div style="font-size: 13px;">{{ user.trial_ends_at.strftime('%b %d') }}</div>
                                {% if user.is_trial_active() %}
                                <div style="font-size: 11px; color: #d97706;">Ends soon</div>
                                {% else %}
                                <div style="font-size: 11px; color: #991b1b;">Ended</div>
                                {% endif %}
                            {% else %}
                                <span style="color: #9ca3af;">-</span>
                            {% endif %}
                        </td>
                        <td>{{ user.created_at.strftime('%b %d, %Y') }}</td>
                        <td style="text-align: right;">
                            <form method="POST" action="{{ url_for('admin.delete_user', user_id=user.id) }}" style="display:inline;" onsubmit="return confirm('Permanently delete {{ user.email }} and all associated data? This cannot be undone.')">
                                <button type="submit" class="btn-delete">Remove</button>
                            </form>
                        </td>
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
        admin_password = os.getenv('ADMIN_PASSWORD')
        
        # Enforce password protection - require ADMIN_PASSWORD to be set
        if not admin_password:
            return render_template_string(ADMIN_LOGIN_HTML, error="Admin access is disabled. ADMIN_PASSWORD environment variable is not set.")
        
        password = request.form.get('password', '')
        if password and password == admin_password:
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
    import os
    # Enforce password protection - require ADMIN_PASSWORD to be set
    admin_password = os.getenv('ADMIN_PASSWORD')
    if not admin_password:
        return "Admin access is disabled. ADMIN_PASSWORD environment variable is not set.", 403
    
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
    import os
    # Enforce password protection - require ADMIN_PASSWORD to be set
    admin_password = os.getenv('ADMIN_PASSWORD')
    if not admin_password:
        return "Admin access is disabled. ADMIN_PASSWORD environment variable is not set.", 403
    
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

