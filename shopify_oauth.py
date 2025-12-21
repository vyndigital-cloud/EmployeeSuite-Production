import os
import hmac
import hashlib
import requests
from flask import Blueprint, request, redirect, session
from models import db, ShopifyStore, User
from flask_login import login_user, current_user
from logging_config import logger

oauth_bp = Blueprint('oauth', __name__)

SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
SHOPIFY_API_SECRET = os.getenv('SHOPIFY_API_SECRET')
# App Store required scopes
SCOPES = 'read_products,read_inventory,read_orders'
REDIRECT_URI = os.getenv('SHOPIFY_REDIRECT_URI', 'https://employeesuite-production.onrender.com/auth/callback')

@oauth_bp.route('/install')
def install():
    """Initiate Shopify OAuth"""
    shop = request.args.get('shop', '').strip()
    
    if not shop:
        return "Missing shop parameter", 400
    
    # Normalize shop domain - add .myshopify.com if not present
    shop = shop.replace('https://', '').replace('http://', '').replace('www.', '')
    if not shop.endswith('.myshopify.com'):
        shop = f"{shop}.myshopify.com"
    
    # Build authorization URL
    auth_url = f"https://{shop}/admin/oauth/authorize"
    params = {
        'client_id': SHOPIFY_API_KEY,
        'scope': SCOPES,
        'redirect_uri': REDIRECT_URI,
        'state': shop  # Use shop as state for simplicity
    }
    
    # For embedded apps, add embedded parameter to redirect URI so callback knows it's embedded
    embedded = request.args.get('embedded')
    if embedded == '1':
        # Append embedded param to redirect URI so callback preserves it
        redirect_uri_with_embedded = f"{REDIRECT_URI}?embedded=1"
        params['redirect_uri'] = redirect_uri_with_embedded
    
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    return redirect(f"{auth_url}?{query_string}")

@oauth_bp.route('/auth/callback')
def callback():
    """Handle Shopify OAuth callback"""
    shop = request.args.get('shop')
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not shop or not code:
        return "Missing required parameters", 400
    
    # Verify HMAC
    hmac_verified = verify_hmac(request.args)
    if not hmac_verified:
        return "HMAC verification failed", 403
    
    # Exchange code for access token
    access_token = exchange_code_for_token(shop, code)
    
    if not access_token:
        return "Failed to get access token", 500
    
    # Get shop information to extract shop_id
    shop_info = get_shop_info(shop, access_token)
    shop_id = shop_info.get('id') if shop_info else None
    
    # Get or create user (for App Store, use shop domain as identifier)
    user = User.query.filter_by(email=f"{shop}@shopify.com").first()
    if not user:
        from datetime import datetime, timedelta
        user = User(
            email=f"{shop}@shopify.com",
            password_hash='',  # OAuth users don't have passwords
            trial_ends_at=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(user)
        db.session.commit()
    
    # Store Shopify credentials with shop_id
    store = ShopifyStore.query.filter_by(shop_url=shop).first()
    if store:
        store.access_token = access_token
        store.shop_id = shop_id
        store.is_active = True
        store.user_id = user.id
    else:
        store = ShopifyStore(
            user_id=user.id,
            shop_url=shop,
            shop_id=shop_id,
            access_token=access_token,
            is_active=True
        )
        db.session.add(store)
    
    db.session.commit()
    
    # Register mandatory compliance webhooks (Shopify requirement)
    register_compliance_webhooks(shop, access_token)
    
    # Log user in
    login_user(user, remember=True)
    session.permanent = True
    
    return redirect('/dashboard')

def verify_hmac(params):
    """Verify Shopify HMAC"""
    hmac_to_verify = params.get('hmac')
    if not hmac_to_verify:
        return False
    
    # Create copy without hmac
    params_copy = dict(params)
    params_copy.pop('hmac', None)
    
    # Build query string
    query_string = '&'.join([f"{k}={v}" for k, v in sorted(params_copy.items())])
    
    # Calculate HMAC
    calculated_hmac = hmac.new(
        SHOPIFY_API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(calculated_hmac, hmac_to_verify)

def exchange_code_for_token(shop, code):
    """Exchange authorization code for access token"""
    url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        'client_id': SHOPIFY_API_KEY,
        'client_secret': SHOPIFY_API_SECRET,
        'code': code
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json().get('access_token')
    
    return None

def get_shop_info(shop, access_token):
    """Get shop information including shop_id"""
    url = f"https://{shop}/admin/api/2024-10/shop.json"
    headers = {
        'X-Shopify-Access-Token': access_token,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('shop', {})
    except Exception as e:
        logger.error(f"Failed to get shop info: {e}")
    
    return None

def register_compliance_webhooks(shop, access_token):
    """
    Register mandatory compliance webhooks via Admin API
    This ensures webhooks are registered even if shopify.app.toml isn't deployed via CLI
    """
    app_url = os.getenv('SHOPIFY_APP_URL', 'https://employeesuite-production.onrender.com')
    api_version = "2024-10"
    
    # Mandatory compliance webhooks
    webhooks = [
        {
            'topic': 'customers/data_request',
            'address': f'{app_url}/webhooks/customers/data_request',
            'format': 'json'
        },
        {
            'topic': 'customers/redact',
            'address': f'{app_url}/webhooks/customers/redact',
            'format': 'json'
        },
        {
            'topic': 'shop/redact',
            'address': f'{app_url}/webhooks/shop/redact',
            'format': 'json'
        }
    ]
    
    headers = {
        'X-Shopify-Access-Token': access_token,
        'Content-Type': 'application/json'
    }
    
    for webhook in webhooks:
        url = f"https://{shop}/admin/api/{api_version}/webhooks.json"
        payload = {'webhook': webhook}
        
        try:
            # Check if webhook already exists
            list_url = f"https://{shop}/admin/api/{api_version}/webhooks.json?topic={webhook['topic']}"
            list_response = requests.get(list_url, headers=headers, timeout=10)
            
            if list_response.status_code == 200:
                existing = list_response.json().get('webhooks', [])
                # Check if webhook with this address already exists
                exists = any(w.get('address') == webhook['address'] for w in existing)
                if exists:
                    continue  # Already registered, skip
            
            # Create webhook
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                logger.info(f"Successfully registered compliance webhook: {webhook['topic']} for shop {shop}")
            else:
                logger.warning(f"Failed to register webhook {webhook['topic']}: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error registering webhook {webhook['topic']}: {e}", exc_info=True)
