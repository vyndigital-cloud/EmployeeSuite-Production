from flask import redirect


def safe_redirect(url, shop=None, host=None):
    """
    Safe redirect for Shopify embedded apps.
    Uses standard HTTP redirect - Shopify handles iframe navigation.
    """
    # For Shopify OAuth URLs, always use standard redirect
    # Shopify's OAuth flow handles the iframe breaking automatically
    if "myshopify.com" in url or "shopify.com" in url:
        return redirect(url)

    # For internal app URLs, use standard redirect
    # The browser/Shopify will handle this correctly
    return redirect(url)
