"""
App Bridge Breakout Utility
Handles iframe authentication redirects for Shopify embedded apps.

Safari and Chrome block 3rd-party cookies in iframes, causing session amnesia.
This utility provides App Bridge-compatible redirects that break out of the iframe.
"""

from flask import render_template_string, request
from logging_config import logger


def is_embedded_request():
    """
    Detect if the request is coming from within a Shopify iframe.
    
    Returns:
        bool: True if request is embedded, False otherwise
    """
    # Check for Shopify-specific headers
    if request.headers.get('X-Shopify-Shop-Domain'):
        return True
    
    # Check for shop parameter (common in embedded apps)
    if request.args.get('shop'):
        return True
    
    # Check for host parameter (Shopify App Bridge)
    if request.args.get('host'):
        return True
    
    # Check for embedded parameter
    if request.args.get('embedded') == '1':
        return True
    
    return False


def create_app_bridge_breakout(redirect_url, shop=None, api_key=None):
    """
    Create an App Bridge breakout page that redirects the parent window.
    
    This is necessary because:
    1. Browsers block cookie setting during iframe redirects
    2. Standard Flask redirects don't work in embedded Shopify apps
    3. We need to use Shopify App Bridge to redirect the parent window
    
    Args:
        redirect_url: The URL to redirect to (e.g., '/auth/login')
        shop: The shop domain (optional, will try to detect from request)
        api_key: Shopify API key (optional, will try to get from env)
    
    Returns:
        Flask response with App Bridge breakout HTML
    """
    import os
    
    # Try to get shop from request if not provided
    if not shop:
        shop = request.args.get('shop') or request.headers.get('X-Shopify-Shop-Domain', '')
    
    # Try to get API key from environment if not provided
    if not api_key:
        api_key = os.getenv('SHOPIFY_API_KEY', '')
    
    # Preserve shop and host parameters in redirect URL
    from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
    
    parsed = urlparse(redirect_url)
    query_params = parse_qs(parsed.query)
    
    # Add shop if we have it and it's not already in the URL
    if shop and 'shop' not in query_params:
        query_params['shop'] = [shop]
    
    # Add host if we have it
    host = request.args.get('host')
    if host and 'host' not in query_params:
        query_params['host'] = [host]
    
    # Rebuild URL with parameters
    new_query = urlencode(query_params, doseq=True)
    redirect_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    
    logger.info(f"🚀 APP BRIDGE BREAKOUT: Redirecting to {redirect_url} (shop: {shop})")
    
    # App Bridge breakout template
    template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Redirecting...</title>
    <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
</head>
<body>
    <div style="text-align: center; padding: 50px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <h2>🔄 Redirecting...</h2>
        <p>Please wait while we redirect you to authenticate.</p>
    </div>
    
    <script>
        // Method 1: Try App Bridge redirect (for embedded apps)
        {% if api_key and shop %}
        try {
            var AppBridge = window['app-bridge'];
            if (AppBridge && AppBridge.createApp) {
                var app = AppBridge.createApp({
                    apiKey: '{{ api_key }}',
                    host: '{{ host }}',
                    forceRedirect: true
                });
                
                var Redirect = AppBridge.actions.Redirect;
                var redirect = Redirect.create(app);
                
                // Redirect to the auth URL
                redirect.dispatch(Redirect.Action.REMOTE, '{{ redirect_url }}');
                
                console.log('✅ App Bridge redirect initiated');
            } else {
                throw new Error('App Bridge not available');
            }
        } catch (e) {
            console.warn('⚠️ App Bridge redirect failed:', e);
            // Fallback to parent window redirect
            if (window.top !== window.self) {
                window.top.location.href = '{{ redirect_url }}';
            } else {
                window.location.href = '{{ redirect_url }}';
            }
        }
        {% else %}
        // Method 2: Parent window redirect (for non-embedded or missing API key)
        if (window.top !== window.self) {
            // We're in an iframe, break out
            window.top.location.href = '{{ redirect_url }}';
        } else {
            // We're not in an iframe, just redirect
            window.location.href = '{{ redirect_url }}';
        }
        {% endif %}
    </script>
</body>
</html>
    """
    
    return render_template_string(
        template,
        redirect_url=redirect_url,
        shop=shop,
        api_key=api_key,
        host=host or ''
    )


def iframe_safe_redirect(redirect_url, shop=None):
    """
    Perform an iframe-safe redirect.
    
    If the request is embedded, returns an App Bridge breakout page.
    Otherwise, returns a standard Flask redirect.
    
    Args:
        redirect_url: The URL to redirect to
        shop: The shop domain (optional)
    
    Returns:
        Flask response (either breakout page or redirect)
    """
    from flask import redirect
    
    if is_embedded_request():
        logger.info(f"🎯 EMBEDDED REQUEST DETECTED: Using App Bridge breakout for {redirect_url}")
        return create_app_bridge_breakout(redirect_url, shop=shop)
    else:
        logger.info(f"🔗 STANDALONE REQUEST: Using standard redirect for {redirect_url}")
        return redirect(redirect_url)


def require_auth_breakout(shop=None):
    """
    Create an authentication breakout page.
    
    This is used when a user needs to authenticate but is in an embedded context.
    
    Args:
        shop: The shop domain (optional)
    
    Returns:
        Flask response with App Bridge breakout to login
    """
    from flask import url_for
    
    login_url = url_for('auth.login', _external=False)
    
    return iframe_safe_redirect(login_url, shop=shop)
