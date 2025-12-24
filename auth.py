from flask import Blueprint, render_template_string, request, redirect, url_for, session, current_app
from flask_login import login_user, logout_user, login_required
from models import db, User
from email_service import send_welcome_email, send_password_reset_email
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import secrets
import os
from input_validation import validate_email, sanitize_input
from logging_config import logger
from embedded_detection import is_embedded_request, get_embedded_params

auth_bp = Blueprint('auth', __name__)

def get_bcrypt():
    """Get bcrypt instance - import from app module"""
    # Import bcrypt from app module (circular import is safe here since we're in a request context)
    try:
        from app import bcrypt
        return bcrypt
    except ImportError:
        # Fallback: create new instance
        from flask_bcrypt import Bcrypt
        return Bcrypt(current_app)

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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f6f6f7;
            color: #202223;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 24px;
            line-height: 1.5;
        }
        .login-container { width: 100%; max-width: 400px; }
        .logo { text-align: center; font-size: 18px; font-weight: 600; color: #202223; margin-bottom: 40px; letter-spacing: -0.2px; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .card { 
            background: #ffffff;
            border: 1px solid #e1e3e5;
            border-radius: 8px;
            padding: 32px;
        }
        .card-title { font-size: 24px; font-weight: 600; color: #202223; margin-bottom: 24px; letter-spacing: -0.3px; }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; font-size: 13px; font-weight: 500; color: #202223; margin-bottom: 6px; }
        .form-input { 
            width: 100%; 
            padding: 10px 12px; 
            border: 1px solid #e1e3e5; 
            border-radius: 6px; 
            font-size: 14px; 
            font-family: inherit; 
            background: #ffffff;
            transition: border-color 0.15s;
        }
        .form-input:focus { 
            outline: none; 
            border-color: #008060;
            box-shadow: 0 0 0 1px #008060;
        }
        .btn { 
            width: 100%; 
            padding: 10px 16px; 
            background: #008060;
            color: #fff; 
            border: none; 
            border-radius: 6px; 
            font-size: 14px; 
            font-weight: 500; 
            cursor: pointer; 
            margin-top: 8px; 
            transition: background 0.15s;
        }
        .btn:hover { 
            background: #006e52;
        }
        .banner-error { 
            background: #fff4f4;
            border: 1px solid #fecaca;
            padding: 12px 16px; 
            border-radius: 6px; 
            margin-bottom: 20px; 
            font-size: 14px; 
            color: #d72c0d;
            font-weight: 400;
        }
        .footer-link { text-align: center; margin-top: 24px; font-size: 14px; color: #6d7175; }
        .footer-link a { color: #008060; text-decoration: none; font-weight: 500; }
        .footer-link a:hover { text-decoration: underline; }
        
        /* Mobile */
        @media (max-width: 768px) {
            body { padding: 20px; }
            .card { padding: 24px; }
            .card-title { font-size: 20px; }
        }
        @media (max-width: 480px) {
            .card { padding: 20px; }
            .card-title { font-size: 18px; }
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
                {% if shop %}<input type="hidden" name="shop" value="{{ shop }}">{% endif %}
                {% if host %}<input type="hidden" name="host" value="{{ host }}">{% endif %}
                {% if embedded %}<input type="hidden" name="embedded" value="{{ embedded }}">{% endif %}
                <div class="form-group">
                    <label class="form-label">Email</label>
                    <input type="email" name="email" class="form-input" required{% if not embedded %} autofocus{% endif %}>
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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f6f6f7;
            color: #202223;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 24px;
            line-height: 1.5;
        }
        .register-container { width: 100%; max-width: 400px; }
        .logo { text-align: center; font-size: 18px; font-weight: 600; color: #202223; margin-bottom: 40px; letter-spacing: -0.2px; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .card { 
            background: #ffffff;
            border: 1px solid #e1e3e5;
            border-radius: 8px;
            padding: 32px;
        }
        .card-title { font-size: 24px; font-weight: 600; color: #202223; margin-bottom: 8px; letter-spacing: -0.3px; }
        .card-subtitle { font-size: 14px; color: #6d7175; margin-bottom: 24px; font-weight: 400; }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; font-size: 13px; font-weight: 500; color: #202223; margin-bottom: 6px; }
        .form-input { 
            width: 100%; 
            padding: 10px 12px; 
            border: 1px solid #e1e3e5; 
            border-radius: 6px; 
            font-size: 14px; 
            font-family: inherit; 
            background: #ffffff;
            transition: border-color 0.15s;
        }
        .form-input:focus { 
            outline: none; 
            border-color: #008060;
            box-shadow: 0 0 0 1px #008060;
        }
        .btn { 
            width: 100%; 
            padding: 10px 16px; 
            background: #008060;
            color: #fff; 
            border: none; 
            border-radius: 6px; 
            font-size: 14px; 
            font-weight: 500; 
            cursor: pointer; 
            margin-top: 8px; 
            transition: background 0.15s;
        }
        .btn:hover { 
            background: #006e52;
        }
        .banner-error { 
            background: #fff4f4;
            border: 1px solid #fecaca;
            padding: 12px 16px; 
            border-radius: 6px; 
            margin-bottom: 20px; 
            font-size: 14px; 
            color: #d72c0d;
            font-weight: 400;
        }
        .footer-link { text-align: center; margin-top: 24px; font-size: 14px; color: #6d7175; }
        .footer-link a { color: #008060; text-decoration: none; font-weight: 500; }
        .footer-link a:hover { text-decoration: underline; }
        
        /* Mobile */
        @media (max-width: 768px) {
            body { padding: 20px; }
            .card { padding: 24px; }
            .card-title { font-size: 20px; }
        }
        @media (max-width: 480px) {
            .card { padding: 20px; }
            .card-title { font-size: 18px; }
        }

    </style>
</head>
<body>
    <div class="register-container">
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
            <a href="/terms" style="color: #999;">Terms</a> • <a href="/privacy" style="color: #999;">Privacy</a>
        </div>
    </div>
</body>
</html>
'''

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Get embedded parameters from both GET (URL params) and POST (form data)
    shop = request.args.get('shop') or request.form.get('shop')
    embedded = request.args.get('embedded') or request.form.get('embedded')
    host = request.args.get('host') or request.form.get('host')
    
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        
        # Input validation
        if not email or not password:
            return render_template_string(LOGIN_HTML, error="Email and password are required", shop=shop, embedded=embedded, host=host)
        
        if not validate_email(email):
            return render_template_string(LOGIN_HTML, error="Invalid email format", shop=shop, embedded=embedded, host=host)
        
        # CRITICAL: Wrap database query in try/except to prevent 500 errors
        try:
            user = User.query.filter_by(email=email).first()
        except Exception as db_error:
            logger.error(f"Database error in login: {db_error}", exc_info=True)
            return render_template_string(LOGIN_HTML, error="System error. Please try again.", shop=shop, embedded=embedded, host=host)
        
        if not user:
            return render_template_string(LOGIN_HTML, error="Invalid email or password", shop=shop, embedded=embedded, host=host)
        
        if not user.password_hash:
            return render_template_string(LOGIN_HTML, error="Invalid email or password", shop=shop, embedded=embedded, host=host)
        
        bcrypt = get_bcrypt()
        if not bcrypt:
            return render_template_string(LOGIN_HTML, error="System error. Please try again.", shop=shop, embedded=embedded, host=host)
        
        try:
            password_valid = bcrypt.check_password_hash(user.password_hash, password)
        except Exception:
            return render_template_string(LOGIN_HTML, error="System error. Please try again.", shop=shop, embedded=embedded, host=host)
        
        if password_valid:
            # CRITICAL: Use unified embedded detection (Safari-compatible)
            # This checks URL params FIRST (not Referer) - works in Safari & Chrome
            is_embedded = is_embedded_request()
            
            # Get params if detection succeeded
            if is_embedded:
                embedded_params = get_embedded_params()
                shop = embedded_params['shop'] or shop
                host = embedded_params['host'] or host
                embedded = '1' if embedded_params['embedded'] else embedded
            
            # CRITICAL: For embedded apps, DO NOT set cookies (Safari blocks them)
            # Session tokens handle ALL authentication for embedded apps
            # Only use cookies for standalone access
            if is_embedded:
                # EMBEDDED: Skip login_user() entirely - no cookies, only session tokens
                # Store user ID in session for reference, but don't use Flask-Login cookies
                # CRITICAL: Don't call login_user() - it sets cookies even with remember=False
                session['user_id'] = user.id
                session['_embedded'] = True  # Mark as embedded session
                session['_authenticated'] = True  # Custom auth flag
                session.permanent = False  # Don't persist embedded sessions
                session.modified = False  # CRITICAL: Don't modify session to avoid cookie headers
                logger.info(f"Login successful for embedded app (session token auth only, no cookies)")
            else:
                # STANDALONE: Use Flask-Login cookies normally
                login_user(user, remember=True)  # Use remember cookie for standalone
                session.permanent = True
                session.modified = True  # Force immediate session save
                logger.info(f"Login successful for standalone access (cookie auth)")
            
            # CRITICAL: Safari blocks server-side redirects in iframes
            # For embedded apps, use JavaScript redirect via App Bridge or render directly
            if is_embedded and shop:
                # SAFARI FIX: Render dashboard HTML directly instead of redirecting
                # This prevents Safari from blocking the redirect in iframe
                from flask import render_template_string
                from app import DASHBOARD_HTML  # Import dashboard HTML
                
                # Get dashboard data (simplified for embedded apps)
                from models import ShopifyStore
                store = ShopifyStore.query.filter_by(shop_url=shop).first() if shop else None
                has_shopify = store is not None
                
                # Render dashboard directly - no redirect needed
                logger.info(f"Safari-friendly login: Rendering dashboard directly for embedded app (shop: {shop})")
                return render_template_string(DASHBOARD_HTML,
                    trial_active=False,
                    days_left=0,
                    is_subscribed=False,
                    has_shopify=has_shopify,
                    has_access=True,  # User just logged in
                    quick_stats={'has_data': False, 'pending_orders': 0, 'total_products': 0, 'low_stock_items': 0},
                    shop_domain=shop or '',
                    SHOPIFY_API_KEY=os.getenv('SHOPIFY_API_KEY', ''))
            
            # For standalone access, redirect to dashboard (Safari allows redirects outside iframes)
            # CRITICAL: Ensure session is saved before redirect
            try:
                session.permanent = True
                session.modified = True
            except Exception:
                pass
            return redirect(url_for('dashboard'))
        
        return render_template_string(LOGIN_HTML, error="Invalid email or password", shop=shop, embedded=embedded, host=host)
    
    # GET request - render login page with embedded params preserved
    # CRITICAL: Wrap in try/except to prevent 500 errors
    try:
        return render_template_string(LOGIN_HTML, shop=shop, embedded=embedded, host=host)
    except Exception as e:
        logger.error(f"Error rendering login page: {e}", exc_info=True)
        # Fallback: render without params if template fails
        try:
            return render_template_string(LOGIN_HTML, shop=None, embedded=None, host=None)
        except Exception:
            # Last resort: return simple error page
            return f"<h1>Login Error</h1><p>Please try again later.</p>", 500

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
        
        bcrypt = get_bcrypt()
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(email=email, password_hash=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        # Send welcome email
        try:
            send_welcome_email(email)
        except Exception:
            pass  # Don't block signup if email fails
        
        # CRITICAL: Use unified embedded detection (Safari-compatible)
        is_embedded = is_embedded_request()
        login_user(new_user, remember=not is_embedded)  # No remember cookie in embedded mode
        session.permanent = True
        session.modified = True  # Force immediate session save (Safari compatibility)
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
        bcrypt = get_bcrypt()
        user.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        
        return redirect(url_for('auth.login'))
    
    return render_template_string(RESET_PASSWORD_HTML, token=token)
