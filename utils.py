from typing import Optional

# Import centralized normalize_shop_url from shopify_utils to avoid duplication
try:
    from shopify_utils import normalize_shop_url
except ImportError:
    # Fallback implementation if shopify_utils is not available
    def normalize_shop_url(shop_url: Optional[str]) -> Optional[str]:
        """Fallback shop URL normalization"""
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

    # For internal app URLs, ensure shop and host are preserved if provided
    if "://" not in url and not url.startswith("//"):
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        if shop and 'shop' not in query_params:
            query_params['shop'] = [shop]
        if host and 'host' not in query_params:
            query_params['host'] = [host]
            
        new_query = urlencode(query_params, doseq=True)
        url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

    return redirect(url)
