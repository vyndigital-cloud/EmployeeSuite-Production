"""
Shopify Webhook Handlers for App Store
Handles app/uninstall and app_subscriptions/update webhooks
"""
from flask import Blueprint, request, jsonify
import hmac
import hashlib
import base64
import os
import requests
from models import db, ShopifyStore, User
from logging_config import logger
from datetime import datetime
from error_logging import error_logger, log_errors

webhook_shopify_bp = Blueprint('webhook_shopify', __name__)

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

@webhook_shopify_bp.route('/webhooks/app/uninstall', methods=['POST'])
@log_errors("WEBHOOK_ERROR")
def app_uninstall():
    """Handle app uninstall webhook from Shopify"""
    try:
        # Log webhook received
        error_logger.log_system_event("WEBHOOK_RECEIVED", {
            'type': 'app/uninstall',
            'shop_domain': request.headers.get('X-Shopify-Shop-Domain', '')
        })
        # Verify webhook signature
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        # Get raw bytes for HMAC verification (not decoded string)
        raw_data = request.get_data(as_text=False)
        if not verify_shopify_webhook(raw_data, hmac_header):
            logger.warning("Invalid webhook signature for app/uninstall")
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        shop_domain = request.headers.get('X-Shopify-Shop-Domain', '')
        if shop_domain:
            shop_domain = shop_domain.lower().replace('https://', '').replace('http://', '').replace('www.', '').strip()
            if not shop_domain.endswith('.myshopify.com') and '.' not in shop_domain:
                shop_domain = f"{shop_domain}.myshopify.com"

        
        if not shop_domain:
            logger.error("Missing shop domain in app/uninstall webhook")
            return jsonify({'error': 'Missing shop domain'}), 400
        
        logger.info(f"App uninstall webhook received for shop: {shop_domain}")
        
        # Find and deactivate the store
        store = ShopifyStore.query.filter_by(shop_url=shop_domain, is_active=True).first()
        if store:
            store.is_active = False
            store.uninstalled_at = datetime.utcnow()
            
            # SCRUB: Clear the access token to ensure it's "stale" and unusable
            store.access_token = None
            
            db.session.commit()
            logger.info(f"Store {shop_domain} marked as uninstalled")
        else:
            logger.warning(f"Store {shop_domain} not found for uninstall")
        
        # Log successful processing
        error_logger.log_system_event("WEBHOOK_PROCESSED", {
            'type': 'app/uninstall',
            'shop_domain': shop_domain,
            'status': 'success'
        })
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        error_logger.log_error(e, "WEBHOOK_PROCESSING_ERROR", {
            'webhook_type': 'app/uninstall',
            'shop_domain': request.headers.get('X-Shopify-Shop-Domain', '')
        })
        logger.error(f"Error handling app/uninstall webhook: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@webhook_shopify_bp.route('/webhooks/app_subscriptions/cancel', methods=['POST'])
@log_errors("WEBHOOK_ERROR")
def app_subscription_cancel():
    """Explicit handler for app subscription cancellation"""
    try:
        # Verify webhook signature
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        raw_data = request.get_data(as_text=False)
        if not verify_shopify_webhook(raw_data, hmac_header):
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        shop_domain = request.headers.get('X-Shopify-Shop-Domain', '')
        
        # Find the store
        store = ShopifyStore.query.filter_by(shop_url=shop_domain).first()
        if store:
            user = User.query.get(store.user_id)
            if user:
                user.is_subscribed = False
                # Wipe cache immediately
                if hasattr(User, '_access_cache') and user.id in User._access_cache:
                    del User._access_cache[user.id]
                logger.info(f"🚫 Subscription CANCELLED for shop {shop_domain}")
            
            db.session.commit()
            
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logger.error(f"Error handling app_subscriptions/cancel: {e}")
        return jsonify({'error': str(e)}), 500


@webhook_shopify_bp.route('/webhooks/app_subscriptions/update', methods=['POST'])
@log_errors("WEBHOOK_ERROR")
def app_subscription_update():
    """Handle app subscription update webhook from Shopify"""
    try:
        # Log webhook received
        error_logger.log_system_event("WEBHOOK_RECEIVED", {
            'type': 'app_subscriptions/update',
            'shop_domain': request.headers.get('X-Shopify-Shop-Domain', '')
        })
        # Verify webhook signature
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        # Get raw bytes for HMAC verification (not decoded string)
        raw_data = request.get_data(as_text=False)
        if not verify_shopify_webhook(raw_data, hmac_header):
            logger.warning("Invalid webhook signature for app_subscriptions/update")
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        shop_domain = request.headers.get('X-Shopify-Shop-Domain', '')
        if shop_domain:
            shop_domain = shop_domain.lower().replace('https://', '').replace('http://', '').replace('www.', '').strip()
            if not shop_domain.endswith('.myshopify.com') and '.' not in shop_domain:
                shop_domain = f"{shop_domain}.myshopify.com"

        
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
