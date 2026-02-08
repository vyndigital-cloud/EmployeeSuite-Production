import secrets
from datetime import datetime, timedelta, timezone

from flask import (
    Blueprint,
    current_app,
    jsonify,  # Add this import
    redirect,
    render_template,  # Changed from render_template_string
    render_template_string,
    request,
    session,
    url_for,
)
from flask_bcrypt import Bcrypt
from flask_login import login_required, login_user, logout_user, current_user

from input_validation import sanitize_input, validate_email
from logging_config import logger
from models import User, db

# Add error handling for imports
try:
    from email_service import send_password_reset_email, send_welcome_email
    EMAIL_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Email service not available: {e}")
    EMAIL_SERVICE_AVAILABLE = False
    
    def send_welcome_email(email):
        logger.info(f"Email service disabled - would send welcome email to {email}")
        return True

    def send_password_reset_email(email, token):
        logger.info(f"Email service disabled - would send password reset to {email}")
        return True

auth_bp = Blueprint("auth", __name__)


def get_bcrypt():
    """Get bcrypt instance using current app"""
    from flask_bcrypt import Bcrypt

    return Bcrypt(current_app)



REGISTER_HTML = """
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
"""


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Get embedded parameters from both GET (URL params) and POST (form data)
    shop = request.args.get("shop") or request.form.get("shop")
    embedded = request.args.get("embedded") or request.form.get("embedded")
    host = request.args.get("host") or request.form.get("host")

    # CRITICAL: For embedded apps, use Shopify OAuth flow - NO login form
    # Embedded apps should redirect to OAuth install endpoint
    # Check Referer header to detect if coming from Shopify admin
    referer = request.headers.get("Referer", "")
    is_from_shopify = "admin.shopify.com" in referer or "myshopify.com" in referer
    is_embedded = embedded == "1" or host or shop or is_from_shopify

    # If embedded but no shop param, try to extract from Referer
    if is_embedded and not shop and is_from_shopify:
        # Try to extract shop from Referer URL
        try:
            from urllib.parse import urlparse

            parsed = urlparse(referer)
            # Referer might be like: https://admin.shopify.com/store/YOUR-SHOP-NAME
            # Or: https://YOUR-SHOP.myshopify.com/admin
            if "myshopify.com" in parsed.netloc:
                shop = parsed.netloc.split(".")[0] + ".myshopify.com"
            elif "/store/" in parsed.path:
                shop_name = parsed.path.split("/store/")[1].split("/")[0]
                shop = f"{shop_name}.myshopify.com"
        except Exception:
            pass

    # If we have shop (from params or extracted), redirect to OAuth
    if is_embedded and shop:
        # Redirect to OAuth install flow (Shopify's embedded auth)
        # Direct URL construction with new OAuth prefix
        install_url = f"/oauth/install?shop={shop}"
        if host:
            install_url += f"&host={host}"
        logger.info(f"Embedded app login request - redirecting to OAuth: {install_url}")
        # Use safe_redirect for embedded apps to break out of iframe
        from utils import safe_redirect

        return safe_redirect(install_url, shop=shop, host=host)

    # If embedded but no shop found, show error message instead of login form
    if is_embedded:
        # render_template_string is already imported at top of file
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Install Required - Employee Suite</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background: #f6f6f7; }
                .container { text-align: center; padding: 40px; max-width: 500px; }
                h1 { font-size: 20px; font-weight: 600; color: #202223; margin-bottom: 16px; }
                p { font-size: 14px; color: #6d7175; line-height: 1.6; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Installation Required</h1>
                <p>Please install Employee Suite from your Shopify admin panel to continue.</p>
            </div>
        </body>
        </html>
        """), 400

    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")

        # Input validation
        if not email or not password:
            return render_template(
                "auth/login.html",
                error="Email and password are required",
                shop=shop,
                embedded=embedded,
                host=host,
            )

        if not validate_email(email):
            return render_template(
                "auth/login.html",
                error="Invalid email format",
                shop=shop,
                embedded=embedded,
                host=host,
            )

        # Handle database connection errors gracefully
        try:
            user = User.query.filter_by(email=email).first()
        except Exception as db_error:
            # If database connection fails, try to fallback to SQLite
            from models import db

            error_msg = str(db_error).lower()
            if (
                "could not translate host" in error_msg
                or "connection" in error_msg
                or "operationalerror" in error_msg
            ):
                logger.warning(
                    f"Database connection error: {db_error}. Attempting fallback to SQLite."
                )
                try:
                    # Switch to SQLite
                    current_app.config["SQLALCHEMY_DATABASE_URI"] = (
                        "sqlite:///employeesuite.db"
                    )
                    db.init_app(current_app._get_current_object())
                    # Retry query
                    user = User.query.filter_by(email=email).first()
                except Exception as fallback_error:
                    logger.error(f"SQLite fallback also failed: {fallback_error}")
                    return render_template(
                        "auth/login.html",
                        error="Database connection error. Please try again in a moment.",
                        shop=shop,
                        embedded=embedded,
                        host=host,
                    )
            else:
                logger.error(f"Database error: {db_error}")
                return render_template(
                    "auth/login.html",
                    error="Database error. Please try again.",
                    shop=shop,
                    embedded=embedded,
                    host=host,
                )

        if not user:
            return render_template(
                "auth/login.html",
                error="Invalid email or password",
                shop=shop,
                embedded=embedded,
                host=host,
            )

        if not user.password_hash:
            return render_template(
                "auth/login.html",
                error="Invalid email or password",
                shop=shop,
                embedded=embedded,
                host=host,
            )

        bcrypt = get_bcrypt()
        if not bcrypt:
            return render_template(
                "auth/login.html",
                error="System error. Please try again.",
                shop=shop,
                embedded=embedded,
                host=host,
            )

        try:
            password_valid = bcrypt.check_password_hash(user.password_hash, password)
        except Exception:
            return render_template(
                "auth/login.html",
                error="System error. Please try again.",
                shop=shop,
                embedded=embedded,
                host=host,
            )

        if password_valid:
            # DETECT EMBEDDED vs STANDALONE for optimal cookie handling
            is_embedded = embedded == "1" or host

            # EMBEDDED APPS: Use session tokens (no remember cookie needed)
            # STANDALONE: Use cookies with remember for better UX
            login_user(
                user, remember=not is_embedded
            )  # No remember cookie in embedded mode
            session.permanent = True
            session.modified = (
                True  # Force immediate session save (Safari compatibility)
            )

            # For embedded apps, session tokens handle auth - cookies are just for compatibility
            # For standalone, cookies are primary auth method
            if is_embedded:
                logger.info(f"Login successful for embedded app (session token auth) - User {user.id}")
            else:
                logger.info(f"Login successful for standalone access (cookie auth) - User {user.id}")

            # Preserve embedded params if this is an embedded app request
            # For embedded apps, redirect to dashboard with params (dashboard handles embedded better)
            if is_embedded and shop:
                # Build URL with all embedded parameters
                params = {"shop": shop, "embedded": "1"}
                if host:
                    params["host"] = host
                dashboard_url = url_for("core.dashboard", **params)
                # Use safe_redirect for embedded apps to break out of iframe
                from utils import safe_redirect

                return safe_redirect(dashboard_url, shop=shop, host=host)
            # For standalone, redirect to dashboard
            # CRITICAL: Ensure session is saved before redirect
            try:
                session.permanent = True
                session.modified = True
            except Exception:
                pass
            return redirect(url_for("core.dashboard"))

        return render_template(
            "auth/login.html",
            error="Invalid email or password",
            shop=shop,
            embedded=embedded,
            host=host,
        )

    # GET request - render login page with embedded params preserved
    return render_template("auth/login.html", shop=shop, embedded=embedded, host=host)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Input validation
        if not email or not password or not confirm_password:
            return render_template_string(
                REGISTER_HTML, error="All fields are required"
            )

        if not validate_email(email):
            return render_template_string(REGISTER_HTML, error="Invalid email format")

        if len(password) < 8:
            return render_template_string(
                REGISTER_HTML, error="Password must be at least 8 characters"
            )

        if password != confirm_password:
            return render_template_string(REGISTER_HTML, error="Passwords don't match")

        if User.query.filter_by(email=email).first():
            return render_template_string(
                REGISTER_HTML, error="Email already registered"
            )

        bcrypt = get_bcrypt()
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        new_user = User(email=email, password_hash=hashed_password)
        
        # Ensure trial is properly set
        new_user.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=7)
        new_user.is_subscribed = False

        db.session.add(new_user)
        db.session.commit()

        # Send welcome email
        if EMAIL_SERVICE_AVAILABLE:
            try:
                send_welcome_email(email)
                logger.info(f"Welcome email sent to {email}")
            except Exception as e:
                logger.error(f"Failed to send welcome email to {email}: {e}")
                # Don't fail registration if email fails
        else:
            logger.info(f"Email service disabled - welcome email not sent to {email}")

        # Register: Use remember cookie for standalone, session tokens for embedded
        is_embedded = request.args.get("embedded") == "1" or request.args.get("host")
        shop = request.args.get("shop")
        host = request.args.get("host")
        login_user(
            new_user, remember=not is_embedded
        )  # No remember cookie in embedded mode
        session.permanent = True
        session.modified = True  # Force immediate session save (Safari compatibility)
        
        logger.info(f"New user registered and logged in - User {new_user.id}")
        
        dashboard_url = url_for("core.dashboard")
        if shop:
            dashboard_url += f"?shop={shop}"
            if host:
                dashboard_url += f"&host={host}&embedded=1"
        # Use safe_redirect for embedded apps to break out of iframe
        from utils import safe_redirect

        return safe_redirect(dashboard_url, shop=shop, host=host)

    return render_template_string(REGISTER_HTML)


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout user - PRESERVE Flask-Login session integrity"""
    # Capture params before logout
    shop = request.args.get("shop")
    host = request.args.get("host")
    embedded = request.args.get("embedded")
    
    # Log the logout
    user_id = current_user.get_id() if current_user.is_authenticated else "unknown"
    logger.info(f"User {user_id} logging out")
    
    # CRITICAL: Clear Flask-Login session properly
    logout_user()
    
    # Clear all session data to prevent stale sessions
    session.clear()
    
    logger.info(f"User {user_id} logged out successfully - session cleared")
    
    # Pass params back to login route so it can handle embedded redirect
    return redirect(url_for("auth.login", shop=shop, host=host, embedded=embedded))


FORGOT_PASSWORD_HTML = """
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
"""

RESET_PASSWORD_HTML = """
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
"""


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    # CRITICAL: For embedded apps, redirect to OAuth (no password reset in embedded mode)
    shop = request.args.get("shop")
    embedded = request.args.get("embedded")
    host = request.args.get("host")
    is_embedded = embedded == "1" or host or shop
    if is_embedded and shop:
        from flask import redirect, url_for

        install_url = f"/oauth/install?shop={shop}"
        if host:
            install_url += f"&host={host}"
        logger.info(
            f"Embedded app forgot-password request - redirecting to OAuth: {install_url}"
        )
        return redirect(install_url)

    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()

        if not email:
            return render_template_string(
                FORGOT_PASSWORD_HTML, error="Email is required"
            )

        if not validate_email(email):
            return render_template_string(
                FORGOT_PASSWORD_HTML, error="Invalid email format"
            )

        user = User.query.filter_by(email=email).first()

        # Always show success message (security: don't reveal if email exists)
        if user and EMAIL_SERVICE_AVAILABLE:
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            user.reset_token = reset_token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            # Send reset email
            try:
                send_password_reset_email(email, reset_token)
                logger.info(f"Password reset email sent to {email}")
            except Exception as e:
                logger.error(f"Failed to send password reset email to {email}: {e}")

        return render_template_string(
            FORGOT_PASSWORD_HTML,
            success="If that email exists, we've sent a password reset link.",
        )

    return render_template_string(FORGOT_PASSWORD_HTML)


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    token = request.args.get("token") or request.form.get("token")

    if not token:
        return render_template_string(
            RESET_PASSWORD_HTML, error="Invalid or missing reset token"
        )

    user = User.query.filter_by(reset_token=token).first()

    if (
        not user
        or not user.reset_token_expires
        or datetime.utcnow() > user.reset_token_expires
    ):
        return render_template_string(
            RESET_PASSWORD_HTML, error="Reset token is invalid or expired"
        )

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not password or not confirm_password:
            return render_template_string(
                RESET_PASSWORD_HTML, error="All fields are required", token=token
            )

        if len(password) < 8:
            return render_template_string(
                RESET_PASSWORD_HTML,
                error="Password must be at least 8 characters",
                token=token,
            )

        if password != confirm_password:
            return render_template_string(
                RESET_PASSWORD_HTML, error="Passwords don't match", token=token
            )

        # Update password
        bcrypt = get_bcrypt()
        user.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()

        logger.info(f"Password reset successful for user {user.id}")

        return redirect(url_for("auth.login"))

    return render_template_string(RESET_PASSWORD_HTML, token=token)
