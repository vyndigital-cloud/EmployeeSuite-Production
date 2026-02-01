"""
Shopify Session Token Authentication - Production Ready
Implements proper session token verification for embedded apps
Required for secure embedded app authentication
"""
import json
import logging
import jwt
import requests
import hashlib
import hmac
from functools import wraps
from flask import request, jsonify, current_app
from models import ShopifyStore
from logging_config import logger

def verify_session_token(token):
    """
    Verify Shopify session token
    Returns decoded payload if valid, None if invalid
    """
    try:
        # Get shop from request
        shop = request.args.get('shop')
        if not shop:
            logger.error("Missing shop parameter in session token verification")
            return None
        
        # Find store to get API secret
        store = ShopifyStore.query.filter_by(shop_domain=shop).first()
        if not store:
            logger.error(f"Store not found for shop: {shop}")
            return None
        
        # Get Shopify API secret
        api_secret = current_app.config.get('SHOPIFY_API_SECRET')
        if not api_secret:
            logger.error("SHOPIFY_API_SECRET not configured")
            return None
        
        # Decode and verify JWT token
        try:
            payload = jwt.decode(
                token,
                api_secret,
                algorithms=['HS256'],
                audience=api_secret
            )
            
            # Verify token claims
            if payload.get('iss') != f"https://{shop}/admin":
                logger.error(f"Invalid issuer in session token: {payload.get('iss')}")
                return None
            
            if payload.get('dest') != f"https://{shop}":
                logger.error(f"Invalid destination in session token: {payload.get('dest')}")
                return None
            
            # Check expiration
            exp = payload.get('exp')
            if exp and exp < (jwt.datetime.now().timestamp()):
                logger.error("Session token has expired")
                return None
            
            logger.info(f"Session token verified successfully for {shop}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.error("Session token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid session token: {e}")
            return None
            
    except Exception as e:
        logger.error(f"Error verifying session token: {e}")
        return None

def require_session_token(f):
    """
    Decorator to require valid session token for API endpoints
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get session token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Missing Authorization header'}), 401
            
            # Extract token from "Bearer <token>" format
            parts = auth_header.split(' ')
            if len(parts) != 2 or parts[0] != 'Bearer':
                return jsonify({'error': 'Invalid Authorization header format'}), 401
            
            token = parts[1]
            
            # Verify session token
            payload = verify_session_token(token)
            if not payload:
                return jsonify({'error': 'Invalid or expired session token'}), 401
            
            # Add verified payload to request context
            request.session_token_payload = payload
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in session token middleware: {e}")
            return jsonify({'error': 'Authentication failed'}), 500
    
    return decorated_function

def verify_shopify_request():
    """
    Verify Shopify request using HMAC verification
    For non-embedded routes or additional security
    """
    try:
        # Get query parameters
        params = request.args
        
        # Get HMAC from query parameters
        hmac_param = params.get('hmac')
        if not hmac_param:
            logger.error("Missing HMAC parameter")
            return False
        
        # Get shop parameter
        shop = params.get('shop')
        if not shop:
            logger.error("Missing shop parameter")
            return False
        
        # Get API secret
        api_secret = current_app.config.get('SHOPIFY_API_SECRET')
        if not api_secret:
            logger.error("SHOPIFY_API_SECRET not configured")
            return False
        
        # Create sorted query string (excluding hmac)
        sorted_params = []
        for key in sorted(params.keys()):
            if key != 'hmac':
                value = params[key]
                sorted_params.append(f"{key}={value}")
        
        query_string = '&'.join(sorted_params)
        
        # Calculate expected HMAC
        expected_hmac = hmac.new(
            api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare HMACs
        if not hmac.compare_digest(expected_hmac, hmac_param):
            logger.error("HMAC verification failed")
            return False
        
        # Verify shop domain format
        if not shop.endswith('.myshopify.com'):
            logger.error(f"Invalid shop domain format: {shop}")
            return False
        
        logger.info(f"Shopify request verified for {shop}")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying Shopify request: {e}")
        return False

def require_shopify_request(f):
    """
    Decorator to require valid Shopify request verification
    For OAuth callbacks and other non-embedded routes
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not verify_shopify_request():
            return jsonify({'error': 'Invalid Shopify request'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

def get_current_shop():
    """
    Get current shop from session token or request parameters
    Returns shop domain if valid, None otherwise
    """
    try:
        # Try session token first (embedded apps)
        if hasattr(request, 'session_token_payload'):
            return request.session_token_payload.get('dest', '').replace('https://', '')
        
        # Fall back to query parameter (non-embedded)
        return request.args.get('shop')
        
    except Exception as e:
        logger.error(f"Error getting current shop: {e}")
        return None

def get_current_store():
    """
    Get current Shopify store from database
    Returns ShopifyStore object if found, None otherwise
    """
    try:
        shop = get_current_shop()
        if not shop:
            return None
        
        return ShopifyStore.query.filter_by(shop_domain=shop).first()
        
    except Exception as e:
        logger.error(f"Error getting current store: {e}")
        return None

def refresh_session_token():
    """
    Refresh expired session token
    Returns new token if successful, None otherwise
    """
    try:
        shop = get_current_shop()
        if not shop:
            return None
        
        store = get_current_store()
        if not store or not store.access_token:
            return None
        
        # Request new session token from Shopify
        url = f"https://{shop}/admin/oauth/access_token"
        
        data = {
            'client_id': current_app.config.get('SHOPIFY_API_KEY'),
            'client_secret': current_app.config.get('SHOPIFY_API_SECRET'),
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'subject_token': store.access_token
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            new_token = token_data.get('access_token')
            
            if new_token:
                logger.info(f"Session token refreshed for {shop}")
                return new_token
        
        logger.error(f"Failed to refresh session token for {shop}")
        return None
        
    except Exception as e:
        logger.error(f"Error refreshing session token: {e}")
        return None

# Session token validation middleware
def validate_session_token_middleware():
    """
    Middleware to validate session tokens for all embedded app requests
    """
    try:
        # Skip validation for non-embedded routes
        if not request.args.get('host'):
            return None
        
        # Get session token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Missing session token'}), 401
        
        # Verify token
        parts = auth_header.split(' ')
        if len(parts) != 2 or parts[0] != 'Bearer':
            return jsonify({'error': 'Invalid token format'}), 401
        
        payload = verify_session_token(parts[1])
        if not payload:
            return jsonify({'error': 'Invalid session token'}), 401
        
        # Store payload for later use
        request.session_token_payload = payload
        
        return None
        
    except Exception as e:
        logger.error(f"Session token middleware error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500
