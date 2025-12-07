import re

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_url(url):
    """Validate Shopify URL format"""
    pattern = r'^[a-zA-Z0-9-]+\.myshopify\.com$'
    return re.match(pattern, url) is not None

from markupsafe import escape

def sanitize_input(text):
    """Enhanced XSS prevention using Flask's escape"""
    if not text:
        return text
    if isinstance(text, str):
        # Use Flask's built-in escape (more secure)
        text = escape(text)
        # Additional defense: remove script tags
        import re
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    return text
