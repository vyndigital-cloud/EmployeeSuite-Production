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
                aud = payload.get('aud')
                
                # LAZY LOAD: Get API key at runtime to ensure it's loaded and strip whitespace
                current_api_key = os.getenv('SHOPIFY_API_KEY', '').strip()
                if current_api_key and (current_api_key.startswith('"') and current_api_key.endswith('"')) or (current_api_key.startswith("'") and current_api_key.endswith("'")):
                    current_api_key = current_api_key[1:-1]
                
                if not current_api_key:
                    logger.error("SHOPIFY_API_KEY environment variable is NOT SET")
                    return jsonify({'error': 'Server configuration error'}), 500
                
                if aud != current_api_key:
                    logger.warning(f"Invalid audience in session token. Received: {aud}, Expected: {current_api_key[:4] + '****'}")
                    logger.warning(f"Length mismatch? Aud: {len(aud) if aud else 0}, Key: {len(current_api_key)}")
                    return jsonify({'error': 'Invalid token audience (API Key mismatch)'}), 401
                
                # Verify destination (should match shop domain)
                dest = payload.get('dest', '')
                if not dest or not dest.endswith('.myshopify.com'):
                    logger.warning(f"Invalid destination in session token: {dest}")
                    return jsonify({'error': 'Invalid token destination'}), 401
                
                request.shop_domain = dest.replace('https://', '').split('/')[0]
                request.session_token_verified = True
                
                logger.debug(f"Session token verified for shop: {request.shop_domain}")
                
                # Auto-login user for embedded app
                try:
                    from models import ShopifyStore, User
                    from flask_login import login_user
                    
                    # Find store by domain
                    store = ShopifyStore.query.filter_by(shop_url=request.shop_domain, is_active=True).first()
                    if store and store.user_id:
                        user = User.query.get(store.user_id)
                        if user and user.has_access():
                            login_user(user)
                            logger.debug(f"Auto-logged in user {user.id} for shop {request.shop_domain}")
                except Exception as e:
                    logger.error(f"Error auto-logging in user: {e}")
                
            except jwt.ExpiredSignatureError:
                logger.warning("Expired session token")
                return jsonify({'error': 'Token has expired'}), 401
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid session token: {e}")
                # Try to decode without verification to debug audience mismatch
                try:
                    debug_payload = jwt.decode(token, options={"verify_signature": False})
                    debug_aud = debug_payload.get('aud')
                    logger.warning(f"DEBUG: Token audience was: {debug_aud}, Expected API Key: {SHOPIFY_API_KEY[:4] + '****' if SHOPIFY_API_KEY else 'None'}")
                except:
                    pass
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
