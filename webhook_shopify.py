"""
Shopify Webhook Handlers for App Store
Handles app/uninstall and app_subscriptions/update webhooks
"""
from flask import Blueprint, request, jsonify
import hmac
import hashlib
import os
import requests
from models import db, ShopifyStore, User
from logging_config import logger
from datetime import datetime

webhook_shopify_bp = Blueprint('webhook_shopify', __name__)

SHOPIFY_API_SECRET = os.getenv('SHOPIFY_API_SECRET')

def verify_shopify_webhook(data, hmac_header):
    """Verify Shopify webhook HMAC signature"""
    if not hmac_header:
        return False
    
    calculated_hmac = hmac.new(
        SHOPIFY_API_SECRET.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(calculated_hmac, hmac_header)

@webhook_shopify_bp.route('/webhooks/app/uninstall', methods=['POST'])
def app_uninstall():
    """Handle app uninstall webhook from Shopify"""
    try:
        # Verify webhook signature
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        if not verify_shopify_webhook(request.data.decode('utf-8'), hmac_header):
            logger.warning("Invalid webhook signature for app/uninstall")
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        shop_domain = request.headers.get('X-Shopify-Shop-Domain')
        
        if not shop_domain:
            logger.error("Missing shop domain in app/uninstall webhook")
            return jsonify({'error': 'Missing shop domain'}), 400
        
        logger.info(f"App uninstall webhook received for shop: {shop_domain}")
        
        # Find and deactivate the store
        store = ShopifyStore.query.filter_by(shop_url=shop_domain, is_active=True).first()
        if store:
            store.is_active = False
            store.uninstalled_at = datetime.utcnow()
            
            # Revoke access token (optional - Shopify already revoked it)
            # But we mark it as inactive
            
            db.session.commit()
            logger.info(f"Store {shop_domain} marked as uninstalled")
        else:
            logger.warning(f"Store {shop_domain} not found for uninstall")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Error handling app/uninstall webhook: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@webhook_shopify_bp.route('/webhooks/app_subscriptions/update', methods=['POST'])
def app_subscription_update():
    """Handle app subscription update webhook from Shopify"""
    try:
        # Verify webhook signature
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        if not verify_shopify_webhook(request.data.decode('utf-8'), hmac_header):
            logger.warning("Invalid webhook signature for app_subscriptions/update")
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        shop_domain = request.headers.get('X-Shopify-Shop-Domain')
        
        if not shop_domain:
            logger.error("Missing shop domain in app_subscriptions/update webhook")
            return jsonify({'error': 'Missing shop domain'}), 400
        
        logger.info(f"App subscription update webhook received for shop: {shop_domain}")
        
        # Find the store
        store = ShopifyStore.query.filter_by(shop_url=shop_domain).first()
        if not store:
            logger.warning(f"Store {shop_domain} not found for subscription update")
            return jsonify({'error': 'Store not found'}), 404
        
        # Update subscription status based on webhook data
        # Shopify sends status: active, cancelled, expired, etc.
        app_subscription = data.get('app_subscription', {})
        status = app_subscription.get('status', '')
        charge_id = app_subscription.get('id', '')
        
        # Update charge_id if provided
        if charge_id:
            store.charge_id = str(charge_id)
        
        # Update user subscription status
        user = User.query.get(store.user_id)
        if user:
            if status == 'active':
                user.is_subscribed = True
                logger.info(f"Subscription activated for shop {shop_domain}")
            elif status in ['cancelled', 'expired', 'declined']:
                user.is_subscribed = False
                logger.info(f"Subscription {status} for shop {shop_domain}")
        
        db.session.commit()
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Error handling app_subscriptions/update webhook: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
