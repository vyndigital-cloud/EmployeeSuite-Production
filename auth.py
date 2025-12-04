from flask import Blueprint, render_template_string, request, redirect, url_for, session
from flask_login import login_user, logout_user, login_required
from models import db, User
from flask_bcrypt import Bcrypt
from email_service import send_welcome_email

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Login - Employee Suite</title>
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
        .logo { text-align: center; font-size: 24px; font-weight: 700; color: #171717; margin-bottom: 16px; }
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        .card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 32px; }
        .card-title { font-size: 20px; font-weight: 600; color: #171717; margin-bottom: 24px; }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; font-size: 14px; font-weight: 500; color: #171717; margin-bottom: 8px; }
        .form-input { width: 100%; padding: 12px; border: 1px solid #e5e5e5; border-radius: 6px; font-size: 14px; font-family: inherit; }
        .form-input:focus { outline: none; border-color: #171717; }
        .btn { width: 100%; padding: 12px; background: #171717; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; margin-top: 8px; }
        .btn:hover { background: #262626; }
        .banner-error { background: #fef2f2; border: 1px solid #fecaca; border-left: 3px solid #dc2626; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 14px; color: #991b1b; }
        .footer-link { text-align: center; margin-top: 20px; font-size: 14px; color: #737373; }
        .footer-link a { color: #171717; text-decoration: none; font-weight: 500; }
        .footer-link a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="login-container">
        <div style="text-align: center; margin-bottom: 40px;">
            <img src="https://i.imgur.com/ujCMb8G.png" alt="Employee Suite" style="width: 120px; height: 120px; filter: drop-shadow(0 8px 16px rgba(114, 176, 94, 0.3)); animation: float 3s ease-in-out infinite;">
        </div>
        <div class="card">
            <h1 class="card-title">Login</h1>
            {% if error %}
            <div class="banner-error">{{ error }}</div>
            {% endif %}
            <form method="POST">
                <div class="form-group">
                    <label class="form-label">Email</label>
                    <input type="email" name="email" class="form-input" required autofocus>
                </div>
                <div class="form-group">
                    <label class="form-label">Password</label>
                    <input type="password" name="password" class="form-input" required>
                </div>
                <button type="submit" class="btn">Login</button>
            </form>
        </div>
        <div class="footer-link">
            Don't have an account? <a href="{{ url_for('auth.register') }}">Sign up</a>
        </div>
        <div style="text-align: center; margin-top: 20px; font-size: 12px; color: #999;">
            <a href="/terms" style="color: #999;">Terms</a> • <a href="/privacy" style="color: #999;">Privacy</a>
        </div>
    </div>
</body>
</html>
'''

REGISTER_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Sign Up - Employee Suite</title>
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
        .register-container { width: 100%; max-width: 400px; }
        .logo { text-align: center; font-size: 24px; font-weight: 700; color: #171717; margin-bottom: 16px; }
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        .card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 32px; }
        .card-title { font-size: 20px; font-weight: 600; color: #171717; margin-bottom: 8px; }
        .card-subtitle { font-size: 14px; color: #737373; margin-bottom: 24px; }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; font-size: 14px; font-weight: 500; color: #171717; margin-bottom: 8px; }
        .form-input { width: 100%; padding: 12px; border: 1px solid #e5e5e5; border-radius: 6px; font-size: 14px; font-family: inherit; }
        .form-input:focus { outline: none; border-color: #171717; }
        .btn { width: 100%; padding: 12px; background: #171717; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; margin-top: 8px; }
        .btn:hover { background: #262626; }
        .banner-error { background: #fef2f2; border: 1px solid #fecaca; border-left: 3px solid #dc2626; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 14px; color: #991b1b; }
        .footer-link { text-align: center; margin-top: 20px; font-size: 14px; color: #737373; }
        .footer-link a { color: #171717; text-decoration: none; font-weight: 500; }
        .footer-link a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="register-container">
        <div style="text-align: center; margin-bottom: 40px;">
            <img src="https://i.imgur.com/ujCMb8G.png" alt="Employee Suite" style="width: 120px; height: 120px; filter: drop-shadow(0 8px 16px rgba(114, 176, 94, 0.3)); animation: float 3s ease-in-out infinite;">
        </div>
        <style>
            @keyframes float {
                0%, 100% { transform: translateY(0px); }
                50% { transform: translateY(-10px); }
            }
        </style>
        <div style="display:none;">
        <div class="card">
            <h1 class="card-title">Start Free Trial</h1>
            <p class="card-subtitle">Your 2-day trial begins immediately</p>
            {% if error %}
            <div class="banner-error">{{ error }}</div>
            {% endif %}
            <form method="POST">
                <div class="form-group">
                    <label class="form-label">Email</label>
                    <input type="email" name="email" class="form-input" required autofocus>
                </div>
                <div class="form-group">
                    <label class="form-label">Password</label>
                    <input type="password" name="password" class="form-input" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Confirm Password</label>
                    <input type="password" name="confirm_password" class="form-input" required>
                </div>
                <button type="submit" class="btn">Start Free Trial</button>
            </form>
        </div>
        <div class="footer-link">
            Already have an account? <a href="{{ url_for('auth.login') }}">Login</a>
        </div>
        <div style="text-align: center; margin-top: 20px; font-size: 12px; color: #999;">
            By signing up, you agree to our <a href="/terms" style="color: #171717;">Terms</a> and <a href="/privacy" style="color: #171717;">Privacy Policy</a>
        </div>
    </div>
</body>
</html>
'''

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            session.permanent = True
            return redirect(url_for('dashboard'))
        
        return render_template_string(LOGIN_HTML, error="Invalid email or password")
    
    return render_template_string(LOGIN_HTML)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return render_template_string(REGISTER_HTML, error="Passwords don't match")
        
        if User.query.filter_by(email=email).first():
            return render_template_string(REGISTER_HTML, error="Email already registered")
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(email=email, password_hash=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        # Send welcome email
        try:
            send_welcome_email(email)
        except:
            pass  # Don't block signup if email fails
        
        login_user(new_user, remember=True)
        session.permanent = True
        return redirect(url_for('dashboard'))
    
    return render_template_string(REGISTER_HTML)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
