import os
import jwt
import time
from functools import wraps
from flask import request, jsonify, g, current_app

def verify_shopify_token(token):
    """
    Verifies a Shopify Session Token (JWT).
    Returns the decoded payload if valid, raises Exception if not.
    """
    secret = os.environ.get('SHOPIFY_API_SECRET')
    if not secret:
        raise Exception("Server config error: Missing Secret")
        
    payload = jwt.decode(
        token, 
        secret, 
        algorithms=['HS256'],
        audience=os.environ.get('SHOPIFY_API_KEY')
    )
    
    # Payload Validation
    # 'dest' field is essentially the shop domain
    dest = payload.get('dest') # e.g. https://my-shop.myshopify.com
    if not dest:
        raise Exception("Invalid Payload: Missing dest")
        
    return payload

def stateless_auth(f):
    """
    ZERO-FLAW AUTH DECORATOR (Stateless)
    
    Verifies the Authorization: Bearer <token> header against the Shopify Store Secret.
    Replaces all cookie-based session logic for API routes.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Extract Token
        auth_header = request.headers.get('Authorization')
        if not auth_header or 'Bearer ' not in auth_header:
            current_app.logger.warning("🚫 Auth Fail: Missing Bearer Token")
            return jsonify({'error': 'Unauthorized: Missing Token'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            # 2. Decode & Verify
            payload = verify_shopify_token(token)
            
            # 3. Context Injection
            dest = payload.get('dest')
            shop = dest.replace('https://', '')
            
            # We trust this token 100%. No DB check needed for simple auth.
            g.shop = shop
            g.jwt_payload = payload
            g.is_stateless = True
            
        except jwt.ExpiredSignatureError:
            current_app.logger.warning("🚫 Auth Fail: Token Expired")
            return jsonify({'error': 'Unauthorized: Token Expired'}), 401
        except jwt.InvalidTokenError as e:
            current_app.logger.warning(f"🚫 Auth Fail: Invalid Token - {str(e)}")
            return jsonify({'error': 'Unauthorized: Invalid Token'}), 401
        except Exception as e:
            current_app.logger.error(f"❌ Auth Error: {str(e)}")
            return jsonify({'error': 'Server Error'}), 500
            
        return f(*args, **kwargs)
        
    return decorated_function
