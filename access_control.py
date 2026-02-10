"""
Access control decorators and utilities
"""

import os
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
                target_path = url_for('billing.subscribe')
                api_key = os.getenv("SHOPIFY_API_KEY", "")
                
                # Use App Bridge breakout to maintain JWT context
                return f'''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <script src="https://unpkg.com/@shopify/app-bridge@3"></script>
                        <script>
                            var AppBridge = window['app-bridge'];
                            var createApp = AppBridge.default;
                            var actions = AppBridge.actions;
                            var Redirect = actions.Redirect;

                            var app = createApp({{
                                apiKey: "{api_key}",
                                host: new URLSearchParams(location.search).get("host"),
                            }});

                            var redirect = Redirect.create(app);
                            redirect.dispatch(Redirect.Action.APP, "{target_path}");
                        </script>
                    </head>
                    <body><p>Subscription required. <a href="{target_path}">Click here</a></p></body>
                    </html>
                ''', 403
                
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
                target_path = url_for('shopify.shopify_settings')
                api_key = os.getenv("SHOPIFY_API_KEY", "")
                return f'''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <script src="https://unpkg.com/@shopify/app-bridge@3"></script>
                        <script>
                            var AppBridge = window['app-bridge'];
                            var createApp = AppBridge.default;
                            var actions = AppBridge.actions;
                            var Redirect = actions.Redirect;

                            var app = createApp({{
                                apiKey: "{api_key}",
                                host: new URLSearchParams(location.search).get("host"),
                            }});

                            var redirect = Redirect.create(app);
                            redirect.dispatch(Redirect.Action.APP, "{target_path}");
                        </script>
                    </head>
                    <body><p>Store connection required. <a href="{target_path}">Click here</a></p></body>
                    </html>
                ''', 403

            return jsonify(
                {
                    "error": "Store connection required",
                    "success": False,
                    "action": "connect_shop",
                }
            ), 403

        return f(*args, **kwargs)

    return decorated_function


def require_zero_trust(f):
    """
    ZERO-TRUST DECORATOR: 
    Validates JWT identity + Authentication + Active Store Connection.
    MANDATORY for all functional routes.
    """
    from session_token_verification import verify_session_token
    
    @verify_session_token
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, redirect, url_for
        
        # 1. Identity Verification (JWT)
        # verify_session_token already handles returning 401 if JWT is present but invalid
        # If no JWT, it falls back to session/cookie check below
        
        # 2. Authentication Check
        if not current_user.is_authenticated:
            if request.accept_mimetypes.accept_html and not request.is_json:
                shop = request.args.get('shop')
                host = request.args.get('host')
                return redirect(url_for('auth.login', shop=shop, host=host))
            return jsonify({"error": "Authentication required", "success": False}), 401

        # 3. Active Store Validation
        if not current_user.active_shop:
            if request.accept_mimetypes.accept_html and not request.is_json:
                shop = request.args.get('shop')
                host = request.args.get('host')
                target_path = url_for('shopify.shopify_settings')
                api_key = os.getenv("SHOPIFY_API_KEY", "")
                return f'''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <script src="https://unpkg.com/@shopify/app-bridge@3"></script>
                        <script>
                            var AppBridge = window['app-bridge'];
                            var createApp = AppBridge.default;
                            var actions = AppBridge.actions;
                            var Redirect = actions.Redirect;

                            var app = createApp({{
                                apiKey: "{api_key}",
                                host: new URLSearchParams(location.search).get("host"),
                            }});

                            var redirect = Redirect.create(app);
                            redirect.dispatch(Redirect.Action.APP, "{target_path}");
                        </script>
                    </head>
                    <body><p>Store connection required. <a href="{target_path}">Click here</a></p></body>
                    </html>
                ''', 403

            return jsonify(
                {
                    "error": "Store connection required",
                    "success": False,
                    "action": "connect_shop",
                }
            ), 403

        # 4. Strict identity match (Ensure request shop domain matches the user's active shop)
        req_shop = getattr(request, 'shop_domain', None) or request.args.get('shop')
        if req_shop and current_user.active_shop != req_shop:
             return jsonify({"error": "Identity mismatch detected. Please refresh.", "success": False}), 403

        return f(*args, **kwargs)

    return decorated_function
