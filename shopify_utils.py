"""
Shopify Utilities
Centralized logic for safe GID parsing, type conversion, and common helpers.
Helps prevent 500 errors from invalid input formats.
"""
import re
import os
from typing import Optional, Union, Any
from flask import request, session

# Use fallback logger if logging_config not available
try:
    from logging_config import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

def normalize_shop_url(shop_url: str) -> Optional[str]:
    """
    Normalize a shop URL with comprehensive validation
    
    Args:
        shop_url: The raw shop URL string.
        
    Returns:
        str: Normalized URL (e.g. 'store.myshopify.com') or None if invalid.
    """
    if not shop_url or not isinstance(shop_url, str):
        return None
        
    try:
        shop = (
            shop_url.lower()
            .replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
            .strip()
        )
        
        # Basic validation
        if not shop or len(shop) > 255 or len(shop) < 3:
            return None
            
        # Remove any path components
        shop = shop.split('/')[0]
        
        # Add .myshopify.com if not present
        if not shop.endswith(".myshopify.com"):
            if "." not in shop:
                shop = f"{shop}.myshopify.com"
            elif not shop.endswith(".myshopify.com"):
                return None  # Invalid domain
        
        # Validate final format
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]\.myshopify\.com$', shop):
            return None
            
        return shop
    except Exception as e:
        logger.warning(f"Error normalizing shop URL '{shop_url}': {e}")
        return None

def validate_csrf_token(req: request, sess: session) -> bool:
    """
    Validate CSRF for Shopify embedded apps.
    
    Args:
        req: Flask request object
        sess: Flask session object
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # For Shopify embedded apps, we can validate the shop parameter
        # and session consistency as a form of CSRF protection
        shop_from_form = req.form.get("shop") or req.args.get("shop", "")
        shop_from_session = sess.get("shop") or sess.get("current_shop", "")

        if shop_from_form and shop_from_session:
            # Normalize both before comparing
            return normalize_shop_url(shop_from_form) == normalize_shop_url(shop_from_session)

        # If no shop validation possible, check referer
        referer = req.headers.get("Referer", "")
        return "myshopify.com" in referer or "admin.shopify.com" in referer
    except Exception as e:
        logger.warning(f"CSRF validation error: {e}")
        return False

def parse_gid(gid: Union[str, int, None]) -> Optional[int]:
    """
    Safely extract the numeric ID from a Shopify Global ID (GID).
    
    Args:
        gid: The GID string (e.g. 'gid://shopify/Shop/12345'), numeric string, or int.
        
    Returns:
        int: The numeric ID if successful.
        None: If parsing fails or input is None.
    """
    if gid is None:
        return None
        
    # If it's already an integer, return it
    if isinstance(gid, int):
        return gid if gid > 0 else None
        
    # If it's a string
    if isinstance(gid, str):
        gid = gid.strip()
        if not gid:
            return None
            
        # Try to parse as pure number string
        if gid.isdigit():
            return int(gid)
            
        # Try to parse as GID URI
        if '/' in gid:
            try:
                # Take the last part after the slash
                last_part = gid.split('/')[-1]
                # Handle potential query params if they exist (though rare in GID)
                clean_id = last_part.split('?')[0]
                if clean_id.isdigit():
                    return int(clean_id)
            except Exception as e:
                logger.warning(f"Failed to parse GID '{gid}': {e}")
                
    logger.warning(f"Could not parse valid ID from: {gid}")
    return None

def format_gid(numeric_id: Union[str, int], resource_type: str = 'Shop') -> str:
    """
    Format a numeric ID into a Shopify Global ID (GID).
    
    Args:
        numeric_id: The numeric ID.
        resource_type: The Shopify resource type (e.g. 'Shop', 'AppSubscription').
        
    Returns:
        str: The formatted GID.
    """
    return f"gid://shopify/{resource_type}/{numeric_id}"

def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """
    Safely convert a value to int.
    
    Args:
        value: The value to convert.
        default: The default value to return if conversion fails.
        
    Returns:
        int: The converted integer or default.
    """
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            value = value.strip()
            if value.isdigit():
                return int(value)
            # Handle negative numbers
            if value.startswith('-') and value[1:].isdigit():
                return int(value)
        return default
    except (ValueError, TypeError, AttributeError):
        return default

def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """
    Safely convert a value to float.
    
    Args:
        value: The value to convert.
        default: The default value to return if conversion fails.
        
    Returns:
        float: The converted float or default.
    """
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def extract_shop_from_request(req: request) -> Optional[str]:
    """
    Extract and normalize shop domain from request.
    
    Args:
        req: Flask request object
        
    Returns:
        str: Normalized shop domain or None
    """
    # Try different sources
    shop = (
        req.args.get('shop') or 
        req.form.get('shop') or 
        req.headers.get('X-Shopify-Shop-Domain') or
        getattr(req, 'shop_domain', None)
    )
    
    if shop:
        return normalize_shop_url(shop)
        
    return None

def is_shopify_request(req: request) -> bool:
    """
    Check if request is from Shopify.
    
    Args:
        req: Flask request object
        
    Returns:
        bool: True if from Shopify
    """
    # Check various indicators
    referer = req.headers.get('Referer', '')
    user_agent = req.headers.get('User-Agent', '')
    
    shopify_indicators = [
        'myshopify.com' in referer,
        'admin.shopify.com' in referer,
        'Shopify' in user_agent,
        req.headers.get('X-Shopify-Shop-Domain'),
        req.headers.get('X-Shopify-Hmac-Sha256'),
        req.args.get('shop'),
        req.form.get('shop')
    ]
    
    return any(shopify_indicators)

def format_currency(amount: Union[str, int, float], currency: str = 'USD') -> str:
    """
    Format amount as currency.
    
    Args:
        amount: The amount to format
        currency: Currency code (default: USD)
        
    Returns:
        str: Formatted currency string
    """
    try:
        amount = float(amount)
        if currency.upper() == 'USD':
            return f"${amount:,.2f}"
        else:
            return f"{amount:,.2f} {currency}"
    except (ValueError, TypeError):
        return f"0.00 {currency}"

def truncate_string(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """
    Truncate string to max length with suffix.
    
    Args:
        text: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        str: Truncated string
    """
    if not text or not isinstance(text, str):
        return ''
        
    if len(text) <= max_length:
        return text
        
    return text[:max_length - len(suffix)] + suffix


def app_bridge_redirect(url: str):
    """
    Return a JavaScript snippet to trigger an App Bridge redirect.
    Bypasses the backend 302 redirect to avoid whitelist checks.
    """
    api_key = os.environ.get("SHOPIFY_API_KEY", "")
    return f'''
    <!DOCTYPE html>
    <html>
        <head>
            <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    const urlParams = new URLSearchParams(window.location.search);
                    let targetUrl = '{url}';
                    
                    // Preserve host if missing from target URL but present in current context
                    if (!targetUrl.includes('host=') && (urlParams.get('host') || window.HOST_PARAM)) {{
                        const host = urlParams.get('host') || window.HOST_PARAM;
                        const sep = targetUrl.indexOf('?') > -1 ? '&' : '?';
                        targetUrl += sep + 'host=' + encodeURIComponent(host);
                    }}

                    if (window.shopify) {{
                        // App Bridge v4 automatically handles navigation
                        window.location.href = targetUrl;
                    }} else {{
                        // Fallback
                        window.location.href = targetUrl;
                    }}
                }});
            </script>
        </head>
        <body>Redirecting...</body>
    </html>
    '''
