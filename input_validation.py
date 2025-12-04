import re

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_url(url):
    """Validate Shopify URL format"""
    pattern = r'^[a-zA-Z0-9-]+\.myshopify\.com$'
    return re.match(pattern, url) is not None

def sanitize_input(text):
    """Basic XSS prevention"""
    if not text:
        return text
    return text.replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
