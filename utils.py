from typing import Optional

def normalize_shop_url(shop_url: Optional[str]) -> Optional[str]:
    """Centralized shop URL normalization - prevents OAuth failures"""
    if not shop_url:
        return None

    # Remove protocol and www
    shop_url = (
        shop_url.lower()
        .replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .strip()
    )

    # Handle path components
    if "/" in shop_url:
        shop_url = shop_url.split("/")[0]

    # Ensure .myshopify.com suffix
    if not shop_url.endswith(".myshopify.com"):
        if "." not in shop_url:
            shop_url = f"{shop_url}.myshopify.com"
        elif not shop_url.endswith(".myshopify.com"):
            raise ValueError("Invalid shop URL format")

    return shop_url


def safe_redirect(url: str, shop: Optional[str] = None, host: Optional[str] = None):
    """
    Safe redirect for Shopify embedded apps.
    Uses standard HTTP redirect - Shopify handles iframe navigation.
    """
    # Import inside function to avoid circular imports
    try:
        from flask import redirect
    except ImportError:
        # Fallback if Flask is not available
        return url
    
    # For Shopify OAuth URLs, always use standard redirect
    # Shopify's OAuth flow handles the iframe breaking automatically
    if "myshopify.com" in url or "shopify.com" in url:
        return redirect(url)

    # For internal app URLs, use standard redirect
    # The browser/Shopify will handle this correctly
    return redirect(url)
