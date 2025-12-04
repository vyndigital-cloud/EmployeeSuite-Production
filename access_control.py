from functools import wraps
from flask import redirect, url_for
from flask_login import current_user

def require_access(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if not current_user.has_access():
            return redirect(url_for('billing.subscribe'))
        
        return f(*args, **kwargs)
    return decorated_function
