"""
UNIFIED EMBEDDED DETECTION - Safari & Chrome compatible
This is the SINGLE SOURCE OF TRUTH for detecting embedded apps
"""

from flask import request

def is_embedded_request():
    """
    Unified embedded detection that works for BOTH Safari and Chrome.
    
    Safari-specific issue: Safari's ITP (Intelligent Tracking Prevention) 
    blocks/modifies Referer headers more aggressively than Chrome.
    
    Detection priority (most reliable first):
    1. URL parameters (host, shop, embedded=1) - MOST RELIABLE (Safari & Chrome)
    2. Shopify headers (X-Shopify-*) - RELIABLE (Safari & Chrome)
    3. Referer/Origin headers - LESS RELIABLE in Safari (ITP blocks them)
    
    Returns:
        bool: True if this is an embedded Shopify app request
    """
    # PRIORITY 1: URL parameters (MOST RELIABLE - works in Safari & Chrome)
    # Shopify ALWAYS sends these for embedded apps
    has_host_param = bool(request.args.get('host'))  # Host is the definitive indicator
    has_shop_param = bool(request.args.get('shop') or request.args.get('shop_domain'))
    has_embedded_flag = request.args.get('embedded') == '1'
    
    if has_host_param or has_shop_param or has_embedded_flag:
        return True
    
    # PRIORITY 2: Shopify-specific headers (RELIABLE - works in Safari & Chrome)
    has_shopify_header = bool(
        request.headers.get('X-Shopify-Shop-Domain') or 
        request.headers.get('X-Shopify-Hmac-Sha256') or
        request.headers.get('X-Shopify-Topic') or
        request.headers.get('X-Shopify-API-Version')
    )
    
    if has_shopify_header:
        return True
    
    # PRIORITY 3: Referer/Origin (LESS RELIABLE in Safari - ITP blocks them)
    # Only use as fallback if URL params and headers aren't available
    referer = request.headers.get('Referer', '').lower()
    origin = request.headers.get('Origin', '').lower()
    
    is_shopify_referer = (
        'admin.shopify.com' in referer or
        '.myshopify.com' in referer or
        'shopify.com' in referer
    )
    
    is_shopify_origin = (
        'admin.shopify.com' in origin or
        '.myshopify.com' in origin or
        'shopify.com' in origin
    )
    
    if is_shopify_referer or is_shopify_origin:
        return True
    
    # PRIORITY 4: Route-based detection (FALLBACK - for security headers)
    # Only use for CSP headers, not for auth/cookie decisions
    # These routes are typically accessed as embedded apps
    is_shopify_route = (
        request.path.startswith('/dashboard') or
        request.path.startswith('/settings') or
        request.path == '/' or
        request.path.startswith('/auth/callback') or
        request.path.startswith('/auth/') or
        request.path.startswith('/login') or
        request.path.startswith('/api/') or
        request.path.startswith('/billing') or
        request.path.startswith('/subscribe') or
        'shopify' in request.path.lower()
    )
    
    # Only use route detection for CSP headers (security), not for auth
    # This prevents false positives in standalone access
    return False  # Don't rely on route alone for embedded detection

def get_embedded_params():
    """
    Extract embedded parameters from request.
    Returns dict with shop, host, embedded flags.
    """
    return {
        'shop': request.args.get('shop') or request.args.get('shop_domain'),
        'host': request.args.get('host'),
        'embedded': request.args.get('embedded') == '1'
    }

