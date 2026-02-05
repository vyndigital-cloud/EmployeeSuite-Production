"""
Access control decorators and utilities
"""

from functools import wraps

from flask import jsonify
from flask_login import current_user


def require_access(f):
    """Decorator to require user has access (trial or subscription)"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required", "success": False}), 401

        if not current_user.has_access():
            # Check if this is a browser request expecting HTML
            from flask import request, redirect, url_for
            if request.accept_mimetypes.accept_html and not request.is_json:
                # Capture params to preserve context
                shop = request.args.get('shop')
                host = request.args.get('host')
                return redirect(url_for('billing.subscribe', error="Subscription required", shop=shop, host=host))
                
            return jsonify(
                {
                    "error": "Subscription required",
                    "success": False,
                    "action": "subscribe",
                }
            ), 403

        return f(*args, **kwargs)

    return decorated_function
