"""
Shopify Utilities
Centralized logic for safe GID parsing, type conversion, and common helpers.
helps prevent 500 errors from invalid input formats.
"""
from typing import Optional, Union, Any
from logging_config import logger
from flask import request, session

def normalize_shop_url(shop_url: str) -> Optional[str]:
    """
    Normalize a shop URL to the standard myshopify.com format.
    
    Args:
        shop_url: The raw shop URL string.
        
    Returns:
        str: Normalized URL (e.g. 'store.myshopify.com') or None if invalid.
    """
    if not shop_url:
        return None
        
    shop = (
        shop_url.lower()
        .replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .strip()
    )
    
    # Basic validation characters
    if not shop or len(shop) > 255:
        return None
        
    if not shop.endswith(".myshopify.com") and "." not in shop:
        shop = f"{shop}.myshopify.com"
        
    return shop

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
    except Exception:
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
        return gid
        
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
                # take the last part after the slash
                last_part = gid.split('/')[-1]
                # handle potential query params if they exist (though rare in GID)
                clean_id = last_part.split('?')[0]
                if clean_id.isdigit():
                    return int(clean_id)
            except Exception as e:
                logger.warning(f"Failed to parse GID '{gid}': {e}")
                pass
                
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
        return int(value)
    except (ValueError, TypeError):
        return default
