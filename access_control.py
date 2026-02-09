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
def require_active_shop(f):
    """Decorator to require user has a connected and active Shopify store"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required", "success": False}), 401

        if not current_user.active_shop:
            # Check if this is a browser request expecting HTML
            from flask import redirect, request, url_for
            if request.accept_mimetypes.accept_html and not request.is_json:
                shop = request.args.get('shop')
                host = request.args.get('host')
                return redirect(url_for('shopify.shopify_settings', error="Store connection required", shop=shop, host=host))

            return jsonify(
                {
                    "error": "Store connection required",
                    "success": False,
                    "action": "connect_shop",
                }
            ), 403

        return f(*args, **kwargs)

    return decorated_function
