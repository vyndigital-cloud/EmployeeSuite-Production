"""
App Bridge Integration for Embedded Shopify Apps
Provides App Bridge initialization and utilities
"""
from flask import Blueprint, render_template_string, request
from flask_login import login_required, current_user
from models import ShopifyStore
import os

app_bridge_bp = Blueprint('app_bridge', __name__)

def get_app_bridge_script():
    """Generate App Bridge initialization script"""
    shop = request.args.get('shop') or get_shop_from_request()
    host = request.args.get('host')  # Shopify provides this for embedded apps
    
    if not shop:
        return ""
    
    return f"""
    <script src="https://cdn.shopify.com/shopifycloud/app-bridge/3.7.0/app-bridge.js"></script>
    <script>
        var AppBridge = window['app-bridge'];
        var createApp = AppBridge.default;
        var Redirect = AppBridge.actions.Redirect;
        
        var app = createApp({{
            apiKey: '{os.getenv("SHOPIFY_API_KEY")}',
            host: '{host or ""}',
            shop: '{shop}'
        }});
        
        // Make app available globally
        window.shopifyApp = app;
        
        // MANDATORY: Fetch and send session tokens for all API requests (January 2025 requirement)
        var sessionToken = '';
        app.getSessionToken().then(function(token) {{
            sessionToken = token;
            // Set default Authorization header for all fetch requests
            var originalFetch = window.fetch;
            window.fetch = function(url, options) {{
                options = options || {{}};
                options.headers = options.headers || {{}};
                if (!options.headers['Authorization'] && sessionToken) {{
                    options.headers['Authorization'] = 'Bearer ' + sessionToken;
                }}
                return originalFetch(url, options);
            }};
            
            // Also set for XMLHttpRequest
            var originalOpen = XMLHttpRequest.prototype.open;
            var originalSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.open = function(method, url, async, user, password) {{
                this._url = url;
                return originalOpen.apply(this, arguments);
            }};
            XMLHttpRequest.prototype.send = function(data) {{
                if (sessionToken && this._url && !this.getRequestHeader('Authorization')) {{
                    this.setRequestHeader('Authorization', 'Bearer ' + sessionToken);
                }}
                return originalSend.apply(this, arguments);
            }};
        }}).catch(function(error) {{
            console.error('Failed to get session token:', error);
        }});
    </script>
    """

def get_shop_from_request():
    """Extract shop domain from request"""
    # Try to get from current user's store
    if current_user.is_authenticated:
        store = ShopifyStore.query.filter_by(
            user_id=current_user.id, 
            is_active=True
        ).first()
        if store:
            return store.shop_url
    
    # Try to get from query params
    return request.args.get('shop') or request.headers.get('X-Shopify-Shop-Domain')

def wrap_with_app_bridge(html_content):
    """Wrap HTML content with App Bridge initialization"""
    app_bridge_script = get_app_bridge_script()
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Employee Suite</title>
        {app_bridge_script}
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
