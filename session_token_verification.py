"""
Shopify Session Token Verification for Embedded Apps
MANDATORY requirement as of January 2025
"""
import jwt
import os
from flask import request, jsonify
from functools import wraps
from logging_config import logger

SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
SHOPIFY_API_SECRET = os.getenv('SHOPIFY_API_SECRET')

def verify_session_token(f):
    """
    Decorator to verify Shopify session token for embedded app requests
    MANDATORY for embedded apps as of January 2025
    
    For embedded apps: Verifies session token from Authorization header
    For non-embedded: Falls back to Flask-Login (if @login_required is also used)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if this is an embedded app request
        auth_header = request.headers.get('Authorization')
        has_session_token = auth_header and auth_header.startswith('Bearer ')
        
        # If session token is present, verify it (embedded app)
        if has_session_token:
            token = auth_header.split(' ')[1] if ' ' in auth_header else None
            if not token:
                return jsonify({'error': 'Invalid token format'}), 401
            
            try:
                # Decode and verify the JWT token
                # Shopify signs session tokens with SHOPIFY_API_SECRET
                payload = jwt.decode(
                    token, 
                    SHOPIFY_API_SECRET, 
                    algorithms=['HS256'],
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_iat": True,
                        "require": ["iss", "dest", "aud", "sub", "exp", "nbf", "iat"]
                    }
                )
                
                # Verify audience (should be API key)
                if payload.get('aud') != SHOPIFY_API_KEY:
                    logger.warning(f"Invalid audience in session token: {payload.get('aud')}")
                    return jsonify({'error': 'Invalid token audience'}), 401
                
                # Verify destination (should match shop domain)
                dest = payload.get('dest', '')
                if not dest or not dest.endswith('.myshopify.com'):
                    logger.warning(f"Invalid destination in session token: {dest}")
                    return jsonify({'error': 'Invalid token destination'}), 401
                
                # Store verified shop domain in request context
                request.shop_domain = dest.replace('https://', '').split('/')[0]
                request.session_token_verified = True
                
                logger.debug(f"Session token verified for shop: {request.shop_domain}")
                
            except jwt.ExpiredSignatureError:
                logger.warning("Expired session token")
                return jsonify({'error': 'Token has expired'}), 401
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid session token: {e}")
                return jsonify({'error': 'Invalid token'}), 401
            except Exception as e:
                logger.error(f"Error verifying session token: {e}", exc_info=True)
                return jsonify({'error': 'Token verification failed'}), 401
        
        # If no session token, route will continue to Flask-Login check (if @login_required is used)
        # This allows non-embedded access to still work
        return f(*args, **kwargs)
    
    return decorated_function

# Removed _is_embedded_app_request - now handled inline in verify_session_token decorator

def get_shop_from_session_token():
    """
    Extract shop domain from verified session token
    Should only be called after verify_session_token decorator
    """
    return getattr(request, 'shop_domain', None)
