from functools import wraps
from flask import redirect, url_for, request, session
from flask_login import current_user
from logging_config import logger

def require_access(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if this is an embedded app request (has shop/host params or session token)
        is_embedded = bool(request.args.get('host') or request.args.get('shop') or 
                          request.headers.get('Authorization', '').startswith('Bearer '))
        
        # For embedded apps, check session['_authenticated'] as backup
        # Primary auth is via session tokens (handled by verify_session_token decorator)
        if is_embedded:
            # Check session backup auth
            if session.get('_authenticated') and session.get('user_id'):
                from models import User
                user = User.query.get(session.get('user_id'))
                if user and user.has_access():
                    # User authenticated via session, continue
                    return f(*args, **kwargs)
            # If no session auth, fall through to Flask-Login check
        
        # For standalone or if embedded session check failed, use Flask-Login
        if not current_user.is_authenticated:
            # For embedded apps, redirect to OAuth install if store not connected
            if is_embedded and request.args.get('shop'):
                from flask import url_for
                shop = request.args.get('shop')
                host = request.args.get('host')
                install_url = url_for('oauth.install', shop=shop, host=host) if host else url_for('oauth.install', shop=shop)
                return redirect(install_url)
            return redirect(url_for('auth.login'))
        
        if not current_user.has_access():
            return redirect(url_for('billing.subscribe'))
        
        return f(*args, **kwargs)
    return decorated_function
