from flask import Blueprint, render_template_string, request, redirect, url_for, session
from flask_login import login_user, logout_user, login_required
from models import db, User
from email_service import send_welcome_email, send_password_reset_email
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import secrets
from input_validation import validate_email, sanitize_input

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()  # Initialize immediately

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
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 50%, #f0f4f8 100%);
            background-attachment: fixed;
            color: #171717;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 24px;
            line-height: 1.6;
        }
        .login-container { width: 100%; max-width: 440px; }
        .logo { text-align: center; font-size: 20px; font-weight: 700; color: #0a0a0a; margin-bottom: 56px; letter-spacing: -0.5px; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .card { 
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 1) 100%);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-radius: 24px;
            padding: 48px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
        }
        .card-title { font-size: 32px; font-weight: 700; color: #0a0a0a; margin-bottom: 40px; letter-spacing: -0.8px; line-height: 1.2; }
        .form-group { margin-bottom: 28px; }
        .form-label { display: block; font-size: 14px; font-weight: 600; color: #0a0a0a; margin-bottom: 10px; letter-spacing: -0.1px; }
        .form-input { 
            width: 100%; 
            padding: 14px 18px; 
            border: 1.5px solid rgba(0, 0, 0, 0.08); 
            border-radius: 12px; 
            font-size: 15px; 
            font-family: inherit; 
            background: rgba(255, 255, 255, 0.8);
            transition: all 0.2s ease;
        }
        .form-input:focus { 
            outline: none; 
            border-color: #3b82f6;
            background: #fff;
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
        }
        .btn { 
            width: 100%; 
            padding: 14px 24px; 
            background: linear-gradient(135deg, #0a0a0a 0%, #262626 100%);
            color: #fff; 
            border: none; 
            border-radius: 12px; 
            font-size: 15px; 
            font-weight: 600; 
            cursor: pointer; 
            margin-top: 12px; 
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        .btn:hover { 
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        }
        .banner-error { 
            background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
            border: 1px solid rgba(239, 68, 68, 0.2);
            padding: 14px 18px; 
            border-radius: 12px; 
            margin-bottom: 28px; 
            font-size: 14px; 
            color: #991b1b;
            font-weight: 500;
        }
        .footer-link { text-align: center; margin-top: 32px; font-size: 14px; color: #64748b; }
        .footer-link a { color: #0a0a0a; text-decoration: none; font-weight: 600; transition: color 0.2s; }
        .footer-link a:hover { color: #3b82f6; }
        
        /* Mobile */
        @media (max-width: 768px) {
            body { padding: 20px; }
            .card { padding: 40px 32px; }
            .card-title { font-size: 28px; }
        }
        @media (max-width: 480px) {
            .card { padding: 32px 24px; }
            .card-title { font-size: 24px; }
        }

    </style>
</head>
<body>
    <div class="login-container">
        <div style="text-align: center; margin-bottom: 24px;">
            <a href="/" style="display: inline-block; text-decoration: none;">
                <img src="https://i.imgur.com/ujCMb8G.png" alt="Employee Suite" style="width: 160px; height: 160px; filter: drop-shadow(0 0 40px rgba(255, 255, 255, 0.8)) drop-shadow(0 0 20px rgba(114, 176, 94, 0.8)); animation: pulse-glow 3s ease-in-out infinite; cursor: pointer;">
            </a>
        </div>
        <style>
            @keyframes pulse-glow {
                0%, 100% { 
                    filter: drop-shadow(0 0 40px rgba(255, 255, 255, 0.8)) drop-shadow(0 0 20px rgba(114, 176, 94, 0.8));
                    transform: scale(1);
                }
                50% { 
                    filter: drop-shadow(0 0 60px rgba(255, 255, 255, 1)) drop-shadow(0 0 30px rgba(114, 176, 94, 1));
                    transform: scale(1.05);
                }
            }
        </style>
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
        <div class="footer-link" style="margin-top: 12px;">
            <a href="{{ url_for('auth.forgot_password') }}">Forgot password?</a>
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
        .register-container { width: 100%; max-width: 440px; }
        .logo { text-align: center; font-size: 24px; font-weight: 700; color: #171717; margin-bottom: 16px; }
        .card { background: #fff; border: 1px solid #e5e5e5; border-radius: 16px; padding: 40px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .card-title { font-size: 20px; font-weight: 600; color: #171717; margin-bottom: 8px; }
        .card-subtitle { font-size: 14px; color: #737373; margin-bottom: 32px; }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; font-size: 14px; font-weight: 600; color: #0a0a0a; margin-bottom: 10px; letter-spacing: 0.2px; }
        .form-input { width: 100%; padding: 13px 16px; border: 1px solid #e5e5e5; border-radius: 8px; font-size: 15px; font-family: inherit; background: #fff; transition: all 0.2s; }
        .form-input:focus { outline: none; border-color: #0a0a0a; box-shadow: 0 0 0 3px rgba(10, 10, 10, 0.05); }
        .btn { width: 100%; padding: 14px; background: #0a0a0a; color: #fff; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer; margin-top: 12px; transition: all 0.2s ease; }
        .btn:hover { background: #262626; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); }
        .banner-error { background: #fef2f2; border: 1px solid #fecaca; border-left: 3px solid #dc2626; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 14px; color: #991b1b; }
        .footer-link { text-align: center; margin-top: 20px; font-size: 14px; color: #737373; }
        .footer-link a { color: #0a0a0a; text-decoration: none; font-weight: 600; }
        .footer-link a:hover { text-decoration: underline; }
        
        /* Mobile Responsive */
        @media (max-width: 768px) {
            body { padding: 16px; padding-top: 3vh; }
            .card { padding: 32px 24px; }
            .logo { font-size: 20px; }
            .card-subtitle { font-size: 13px; }
        }
        @media (max-width: 480px) {
            .card { padding: 28px 20px; }
            .card-title { font-size: 18px; }
        }

    </style>
</head>
<body>
    <div class="register-container">
        <div style="text-align: center; margin-bottom: 32px;">
            <a href="/" style="text-decoration: none; color: inherit; display: inline-flex; align-items: center; gap: 10px; font-weight: 600;">
                <span style="font-size: 24px;">🚀</span>
                <span style="font-size: 20px;">Employee Suite</span>
            </a>
        </div>
        <div class="card">
            <h1 class="card-title">Start Free Trial</h1>
            <p class="card-subtitle">Your 7-day trial begins immediately</p>
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
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        
        # Input validation
        if not email or not password:
            return render_template_string(LOGIN_HTML, error="Email and password are required")
        
        if not validate_email(email):
            return render_template_string(LOGIN_HTML, error="Invalid email format")
        
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
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Input validation
        if not email or not password or not confirm_password:
            return render_template_string(REGISTER_HTML, error="All fields are required")
        
        if not validate_email(email):
            return render_template_string(REGISTER_HTML, error="Invalid email format")
        
        if len(password) < 8:
            return render_template_string(REGISTER_HTML, error="Password must be at least 8 characters")
        
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
        except Exception:
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

FORGOT_PASSWORD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Forgot Password - Employee Suite</title>
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
        .container { width: 100%; max-width: 440px; }
        .card { background: #fff; border: 1px solid #e5e5e5; border-radius: 16px; padding: 40px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .card-title { font-size: 20px; font-weight: 600; color: #171717; margin-bottom: 24px; }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; font-size: 14px; font-weight: 600; color: #0a0a0a; margin-bottom: 10px; }
        .form-input { width: 100%; padding: 13px 16px; border: 1.5px solid #d4d4d4; border-radius: 8px; font-size: 15px; font-family: inherit; background: #fafafa; }
        .form-input:focus { outline: none; border-color: #72b05e; box-shadow: 0 0 0 3px rgba(114, 176, 94, 0.1); background: #fff; }
        .btn { width: 100%; padding: 14px; background: #4a7338; color: #fff; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; margin-top: 12px; }
        .btn:hover { background: #3a5c2a; }
        .banner-error { background: #fef2f2; border: 1px solid #fecaca; border-left: 3px solid #dc2626; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 14px; color: #991b1b; }
        .banner-success { background: #f0fdf4; border: 1px solid #86efac; border-left: 3px solid #16a34a; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 14px; color: #166534; }
        .footer-link { text-align: center; margin-top: 20px; font-size: 14px; color: #737373; }
        .footer-link a { color: #0a0a0a; text-decoration: none; font-weight: 600; }
        
        /* Mobile Responsive */
        @media (max-width: 768px) {
            body { padding: 16px; padding-top: 3vh; }
            .card { padding: 32px 24px; }
        }
        @media (max-width: 480px) {
            .card { padding: 28px 20px; }
            .card-title { font-size: 18px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1 class="card-title">Reset Password</h1>
            {% if error %}
            <div class="banner-error">{{ error }}</div>
            {% endif %}
            {% if success %}
            <div class="banner-success">{{ success }}</div>
            {% endif %}
            {% if not success %}
            <form method="POST">
                <div class="form-group">
                    <label class="form-label">Email</label>
                    <input type="email" name="email" class="form-input" required autofocus>
                </div>
                <button type="submit" class="btn">Send Reset Link</button>
            </form>
            {% endif %}
        </div>
        <div class="footer-link">
            <a href="{{ url_for('auth.login') }}">Back to Login</a>
        </div>
    </div>
</body>
</html>
'''

RESET_PASSWORD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Reset Password - Employee Suite</title>
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
        .container { width: 100%; max-width: 440px; }
        .card { background: #fff; border: 1px solid #e5e5e5; border-radius: 16px; padding: 40px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .card-title { font-size: 20px; font-weight: 600; color: #171717; margin-bottom: 24px; }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; font-size: 14px; font-weight: 600; color: #0a0a0a; margin-bottom: 10px; }
        .form-input { width: 100%; padding: 13px 16px; border: 1.5px solid #d4d4d4; border-radius: 8px; font-size: 15px; font-family: inherit; background: #fafafa; }
        .form-input:focus { outline: none; border-color: #72b05e; box-shadow: 0 0 0 3px rgba(114, 176, 94, 0.1); background: #fff; }
        .btn { width: 100%; padding: 14px; background: #4a7338; color: #fff; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; margin-top: 12px; }
        .btn:hover { background: #3a5c2a; }
        .banner-error { background: #fef2f2; border: 1px solid #fecaca; border-left: 3px solid #dc2626; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 14px; color: #991b1b; }
        .footer-link { text-align: center; margin-top: 20px; font-size: 14px; color: #737373; }
        .footer-link a { color: #0a0a0a; text-decoration: none; font-weight: 600; }
        
        /* Mobile Responsive */
        @media (max-width: 768px) {
            body { padding: 16px; padding-top: 3vh; }
            .card { padding: 32px 24px; }
        }
        @media (max-width: 480px) {
            .card { padding: 28px 20px; }
            .card-title { font-size: 18px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1 class="card-title">Set New Password</h1>
            {% if error %}
            <div class="banner-error">{{ error }}</div>
            {% endif %}
            <form method="POST">
                <input type="hidden" name="token" value="{{ token }}">
                <div class="form-group">
                    <label class="form-label">New Password</label>
                    <input type="password" name="password" class="form-input" required autofocus>
                </div>
                <div class="form-group">
                    <label class="form-label">Confirm Password</label>
                    <input type="password" name="confirm_password" class="form-input" required>
                </div>
                <button type="submit" class="btn">Reset Password</button>
            </form>
        </div>
        <div class="footer-link">
            <a href="{{ url_for('auth.login') }}">Back to Login</a>
        </div>
    </div>
</body>
</html>
'''

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        
        if not email:
            return render_template_string(FORGOT_PASSWORD_HTML, error="Email is required")
        
        if not validate_email(email):
            return render_template_string(FORGOT_PASSWORD_HTML, error="Invalid email format")
        
        user = User.query.filter_by(email=email).first()
        
        # Always show success message (security: don't reveal if email exists)
        if user:
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            user.reset_token = reset_token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            # Send reset email
            try:
                send_password_reset_email(email, reset_token)
            except Exception:
                pass  # Don't reveal if email failed
        
        return render_template_string(FORGOT_PASSWORD_HTML, success="If that email exists, we've sent a password reset link.")
    
    return render_template_string(FORGOT_PASSWORD_HTML)

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    token = request.args.get('token') or request.form.get('token')
    
    if not token:
        return render_template_string(RESET_PASSWORD_HTML, error="Invalid or missing reset token")
    
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.reset_token_expires or datetime.utcnow() > user.reset_token_expires:
        return render_template_string(RESET_PASSWORD_HTML, error="Reset token is invalid or expired")
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not password or not confirm_password:
            return render_template_string(RESET_PASSWORD_HTML, error="All fields are required", token=token)
        
        if len(password) < 8:
            return render_template_string(RESET_PASSWORD_HTML, error="Password must be at least 8 characters", token=token)
        
        if password != confirm_password:
            return render_template_string(RESET_PASSWORD_HTML, error="Passwords don't match", token=token)
        
        # Update password
        user.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        
        return redirect(url_for('auth.login'))
    
    return render_template_string(RESET_PASSWORD_HTML, token=token)
