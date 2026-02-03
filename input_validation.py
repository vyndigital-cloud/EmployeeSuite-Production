"""
Input Validation and Sanitization
"""
import re
from typing import Optional, Any

def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email.strip()) is not None

def validate_url(url: str) -> bool:
    """Validate Shopify URL format"""
    if not url or not isinstance(url, str):
        return False
        
    pattern = r'^[a-zA-Z0-9-]+\.myshopify\.com$'
    return re.match(pattern, url.strip()) is not None

def validate_shop_domain(shop: str) -> bool:
    """Validate shop domain format"""
    if not shop or not isinstance(shop, str):
        return False
        
    shop = shop.strip().lower()
    
    # Remove protocol if present
    shop = shop.replace('https://', '').replace('http://', '')
    
    # Check if it's a valid myshopify.com domain
    if not shop.endswith('.myshopify.com'):
        return False
        
    # Extract shop name
    shop_name = shop.replace('.myshopify.com', '')
    
    # Validate shop name (alphanumeric and hyphens only)
    if not re.match(r'^[a-zA-Z0-9-]+$', shop_name):
        return False
        
    # Shop name length limits
    if len(shop_name) < 3 or len(shop_name) > 60:
        return False
        
    return True

def sanitize_input(text: Any) -> Any:
    """Enhanced XSS prevention using Flask's escape"""
    if not text:
        return text
        
    if isinstance(text, str):
        try:
            from markupsafe import escape
            # Use Flask's built-in escape (more secure)
            text = escape(text)
            
            # Additional defense: remove script tags and javascript
            text = re.sub(r'<script[^>]*>.*?</script>', '', str(text), flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(r'javascript:', '', str(text), flags=re.IGNORECASE)
            text = re.sub(r'on\w+\s*=', '', str(text), flags=re.IGNORECASE)  # Remove event handlers
            
        except ImportError:
            # Fallback if markupsafe not available
            text = str(text).replace('<', '&lt;').replace('>', '&gt;')
            
    return text

def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not password or not isinstance(password, str):
        return False, "Password is required"
        
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
        
    if len(password) > 128:
        return False, "Password is too long (max 128 characters)"
        
    # Check for at least one letter and one number
    if not re.search(r'[a-zA-Z]', password):
        return False, "Password must contain at least one letter"
        
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
        
    return True, None

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    if not filename:
        return "unnamed_file"
        
    # Remove path separators and dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\.\.+', '.', filename)  # Remove multiple dots
    filename = filename.strip('. ')  # Remove leading/trailing dots and spaces
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
        
    return filename or "unnamed_file"

def validate_json_input(data: Any, required_fields: list = None) -> tuple[bool, Optional[str]]:
    """
    Validate JSON input data
    
    Args:
        data: The JSON data to validate
        required_fields: List of required field names
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Invalid JSON format"
        
    if required_fields:
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
            
    return True, None
