import os
import hmac
import hashlib
import requests
from flask import Blueprint, request, redirect, session
from models import db, ShopifyStore, User
from flask_login import login_user, current_user

oauth_bp = Blueprint('oauth', __name__)

SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
SHOPIFY_API_SECRET = os.getenv('SHOPIFY_API_SECRET')
SCOPES = 'read_products,read_inventory,read_orders'
REDIRECT_URI = 'https://employeesuite-production.onrender.com/auth/callback'

@oauth_bp.route('/install')
def install():
    """Initiate Shopify OAuth"""
    shop = request.args.get('shop')
    
    if not shop:
        return "Missing shop parameter", 400
    
    # Build authorization URL
    auth_url = f"https://{shop}/admin/oauth/authorize"
    params = {
        'client_id': SHOPIFY_API_KEY,
        'scope': SCOPES,
        'redirect_uri': REDIRECT_URI,
        'state': shop  # Use shop as state for simplicity
    }
    
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
    
    # Get or create user (for now, auto-create)
    user = User.query.filter_by(email=f"{shop}@shopify.com").first()
    if not user:
        from datetime import datetime, timedelta
        user = User(
            email=f"{shop}@shopify.com",
            password_hash='',  # OAuth users don't have passwords
            trial_ends_at=datetime.utcnow() + timedelta(days=2)
        )
        db.session.add(user)
        db.session.commit()
    
    # Store Shopify credentials
    store = ShopifyStore.query.filter_by(user_id=user.id, shop_url=shop).first()
    if store:
        store.access_token = access_token
        store.is_active = True
    else:
        store = ShopifyStore(
            user_id=user.id,
            shop_url=shop,
            access_token=access_token,
            is_active=True
        )
        db.session.add(store)
    
    db.session.commit()
    
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
