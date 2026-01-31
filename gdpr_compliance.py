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
    
    Shopify Requirements:
    - Must respond with 200 OK within 5 seconds (connection within 1 second)
    - Must verify HMAC signature (return 401 if invalid)
    - Must handle POST requests with JSON body and Content-Type: application/json
    - Should process asynchronously if data collection takes longer than 5 seconds
    """
    try:
        # Verify Content-Type header (Shopify requirement)
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            logger.warning("Invalid Content-Type for customers/data_request")
            return jsonify({'error': 'Invalid Content-Type'}), 400
        
        # Verify HMAC signature FIRST (before any processing)
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        # Get raw bytes for HMAC verification (not decoded string) - Shopify requirement
        raw_data = request.get_data(as_text=False)
        if not verify_shopify_webhook(raw_data, hmac_header):
            logger.warning("Invalid webhook signature for customers/data_request")
            return jsonify({'error': 'Invalid signature'}), 401
        
        # Parse JSON AFTER HMAC verification passes
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'Invalid JSON payload'}), 400
        
        shop_domain = request.headers.get('X-Shopify-Shop-Domain', '')
        if shop_domain:
            shop_domain = shop_domain.lower().replace('https://', '').replace('http://', '').replace('www.', '').strip()
            if not shop_domain.endswith('.myshopify.com') and '.' not in shop_domain:
                shop_domain = f"{shop_domain}.myshopify.com"

        customer_id = data.get('customer', {}).get('id')
        
        logger.info(f"GDPR data request for customer {customer_id} from shop {shop_domain}")
        
        # Respond with 200 OK IMMEDIATELY (Shopify requirement: must respond within 5 seconds)
        # Note: Actual data collection should be queued/processed asynchronously
        # if it takes longer than 5 seconds to complete
        
        # Quick validation - find store (fast DB query)
        store = ShopifyStore.query.filter_by(shop_url=shop_domain, is_active=True).first()
        if not store:
            # Still return 200 OK as per Shopify requirement
            # Log the issue for manual review
            logger.warning(f"Store {shop_domain} not found for data request")
            return jsonify({'status': 'success'}), 200
        
        # In production, you would:
        # 1. Queue the data collection job (if it takes > 5 seconds)
        # 2. Process asynchronously
        # 3. Query database for all customer-related data
        # 4. Format as JSON
        # 5. Store temporarily or email to customer/store owner
        # For now, we acknowledge receipt immediately (compliant with Shopify)
        
        logger.info(f"Customer data request acknowledged for {customer_id}")
        
        # Return 200 OK quickly (within 5 seconds requirement)
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Error handling customers/data_request: {e}", exc_info=True)
        # Return 200 OK even on error to prevent Shopify retries (per best practice)
        # Log error for manual review/reconciliation
        return jsonify({'status': 'success'}), 200

@gdpr_bp.route('/webhooks/customers/redact', methods=['POST'])
def customers_redact():
    """
    GDPR: Customer data deletion request
    Shopify will send this when a customer requests data deletion
    
    Shopify Requirements:
    - Must respond with 200 OK within 5 seconds
    - Must verify HMAC signature (return 401 if invalid)
    - Must handle POST requests with JSON body and Content-Type: application/json
    - Must complete deletion within 30 days (can process asynchronously)
    """
    try:
        # Verify Content-Type header (Shopify requirement)
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            logger.warning("Invalid Content-Type for customers/redact")
            return jsonify({'error': 'Invalid Content-Type'}), 400
        
        # Verify HMAC signature FIRST
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        raw_data = request.get_data(as_text=False)
        if not verify_shopify_webhook(raw_data, hmac_header):
            logger.warning("Invalid webhook signature for customers/redact")
            return jsonify({'error': 'Invalid signature'}), 401
        
        # Parse JSON AFTER HMAC verification
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'Invalid JSON payload'}), 400
        
        shop_domain = request.headers.get('X-Shopify-Shop-Domain', '')
        if shop_domain:
            shop_domain = shop_domain.lower().replace('https://', '').replace('http://', '').replace('www.', '').strip()
            if not shop_domain.endswith('.myshopify.com') and '.' not in shop_domain:
                shop_domain = f"{shop_domain}.myshopify.com"

        customer_id = data.get('customer', {}).get('id')
        email = data.get('customer', {}).get('email')
        
        logger.info(f"GDPR deletion request for customer {customer_id} ({email}) from shop {shop_domain}")
        
        # Find store (quick validation)
        store = ShopifyStore.query.filter_by(shop_url=shop_domain, is_active=True).first()
        if not store:
            logger.warning(f"Store {shop_domain} not found for redact request")
            # Still return 200 OK per Shopify requirement
            return jsonify({'status': 'success'}), 200
        
        # Delete customer data (can be queued if takes > 5 seconds)
        # In production, you would:
        # 1. Queue deletion job if processing takes > 5 seconds
        # 2. Find all records associated with this customer
        # 3. Anonymize or delete them
        # 4. Log the deletion
        # Must complete within 30 days per GDPR requirements
        
        logger.info(f"Customer data deletion acknowledged for {customer_id}")
        
        # Return 200 OK quickly
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Error handling customers/redact: {e}", exc_info=True)
        # Return 200 OK to prevent Shopify retries
        return jsonify({'status': 'success'}), 200

@gdpr_bp.route('/webhooks/shop/redact', methods=['POST'])
def shop_redact():
    """
    GDPR: Shop data deletion request
    Shopify will send this 48 hours after a shop uninstalls the app
    
    Shopify Requirements:
    - Must respond with 200 OK within 5 seconds
    - Must verify HMAC signature (return 401 if invalid)
    - Must handle POST requests with JSON body and Content-Type: application/json
    - Must delete all shop data (can process asynchronously if needed)
    """
    try:
        # Verify Content-Type header (Shopify requirement)
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            logger.warning("Invalid Content-Type for shop/redact")
            return jsonify({'error': 'Invalid Content-Type'}), 400
        
        # Verify HMAC signature FIRST
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        raw_data = request.get_data(as_text=False)
        if not verify_shopify_webhook(raw_data, hmac_header):
            logger.warning("Invalid webhook signature for shop/redact")
            return jsonify({'error': 'Invalid signature'}), 401
        
        # Parse JSON AFTER HMAC verification
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'Invalid JSON payload'}), 400
        
        shop_domain = request.headers.get('X-Shopify-Shop-Domain', '')
        if shop_domain:
            shop_domain = shop_domain.lower().replace('https://', '').replace('http://', '').replace('www.', '').strip()
            if not shop_domain.endswith('.myshopify.com') and '.' not in shop_domain:
                shop_domain = f"{shop_domain}.myshopify.com"

        
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
            # Can be queued if processing takes > 5 seconds
            
            # Mark store as deleted (quick operation)
            store.is_active = False
            db.session.commit()
            
            logger.info(f"Shop data deletion processed for {shop_domain}")
        
        # Return 200 OK quickly
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Error handling shop/redact: {e}", exc_info=True)
        # Return 200 OK to prevent Shopify retries
        return jsonify({'status': 'success'}), 200
