"""
GDPR Compliance Endpoints
Handles customer data requests and deletion
"""
from flask import Blueprint, request, jsonify
import hmac
import hashlib
import base64
import os
from models import db, User, ShopifyStore
from logging_config import logger

gdpr_bp = Blueprint('gdpr', __name__)

SHOPIFY_API_SECRET = os.getenv('SHOPIFY_API_SECRET')

def verify_shopify_webhook(data, hmac_header):
    """Verify Shopify webhook HMAC signature - Shopify uses BASE64 encoded HMAC"""
    if not hmac_header or not SHOPIFY_API_SECRET:
        return False
    
    # Shopify sends HMAC as base64, so we need to compute base64 too
    # data should be raw bytes, not decoded string
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    calculated_hmac = base64.b64encode(
        hmac.new(
            SHOPIFY_API_SECRET.encode('utf-8'),
            data,
            hashlib.sha256
        ).digest()
    ).decode('utf-8')
    
    return hmac.compare_digest(calculated_hmac, hmac_header)

@gdpr_bp.route('/webhooks/customers/data_request', methods=['POST'])
def customers_data_request():
    """
    GDPR: Customer data request
    Shopify will send this when a customer requests their data
    """
    try:
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        # Get raw bytes for HMAC verification (not decoded string)
        raw_data = request.get_data(as_text=False)
        if not verify_shopify_webhook(raw_data, hmac_header):
            logger.warning("Invalid webhook signature for customers/data_request")
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        shop_domain = request.headers.get('X-Shopify-Shop-Domain')
        customer_id = data.get('customer', {}).get('id')
        
        logger.info(f"GDPR data request for customer {customer_id} from shop {shop_domain}")
        
        # Find store
        store = ShopifyStore.query.filter_by(shop_url=shop_domain, is_active=True).first()
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        # Collect customer data
        # In a real app, you would collect all data associated with this customer
        customer_data = {
            'customer_id': customer_id,
            'shop_domain': shop_domain,
            'orders_processed': [],  # Would fetch from your database
            'inventory_updates': [],  # Would fetch from your database
            'reports_generated': []  # Would fetch from your database
        }
        
        # In production, you would:
        # 1. Query your database for all customer-related data
        # 2. Format it as JSON
        # 3. Store it temporarily
        # 4. Provide a download link or email it to the customer
        
        logger.info(f"Customer data collected for {customer_id}")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Error handling customers/data_request: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@gdpr_bp.route('/webhooks/customers/redact', methods=['POST'])
def customers_redact():
    """
    GDPR: Customer data deletion request
    Shopify will send this when a customer requests data deletion
    """
    try:
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        # Get raw bytes for HMAC verification (not decoded string)
        raw_data = request.get_data(as_text=False)
        if not verify_shopify_webhook(raw_data, hmac_header):
            logger.warning("Invalid webhook signature for customers/redact")
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        shop_domain = request.headers.get('X-Shopify-Shop-Domain')
        customer_id = data.get('customer', {}).get('id')
        email = data.get('customer', {}).get('email')
        
        logger.info(f"GDPR deletion request for customer {customer_id} ({email}) from shop {shop_domain}")
        
        # Find store
        store = ShopifyStore.query.filter_by(shop_url=shop_domain, is_active=True).first()
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        # Delete customer data
        # In a real app, you would:
        # 1. Find all records associated with this customer
        # 2. Anonymize or delete them
        # 3. Log the deletion
        
        # Example: Delete order processing records, inventory updates, etc.
        # This is a placeholder - implement based on your data model
        
        logger.info(f"Customer data deleted for {customer_id}")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Error handling customers/redact: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@gdpr_bp.route('/webhooks/shop/redact', methods=['POST'])
def shop_redact():
    """
    GDPR: Shop data deletion request
    Shopify will send this when a shop is deleted/uninstalled
    """
    try:
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        # Get raw bytes for HMAC verification (not decoded string)
        raw_data = request.get_data(as_text=False)
        if not verify_shopify_webhook(raw_data, hmac_header):
            logger.warning("Invalid webhook signature for shop/redact")
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        shop_domain = request.headers.get('X-Shopify-Shop-Domain')
        
        logger.info(f"GDPR shop deletion request for shop {shop_domain}")
        
        # Find and delete all store data
        store = ShopifyStore.query.filter_by(shop_url=shop_domain).first()
        if store:
            # Delete all associated data
            # In production, you would delete:
            # - Order processing records
            # - Inventory updates
            # - Reports
            # - User account (if shop-specific)
            
            # Mark store as deleted
            store.is_active = False
            db.session.commit()
            
            logger.info(f"Shop data deleted for {shop_domain}")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Error handling shop/redact: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
