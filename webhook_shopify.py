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
    """
    Handle app uninstall webhook from Shopify - ASYNC & IDEMPOTENT
    """
    try:
        # 1. Verify Signature
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        raw_data = request.get_data(as_text=False)
        if not verify_shopify_webhook(raw_data, hmac_header):
            logger.warning("Invalid webhook signature for app/uninstall")
            return jsonify({'error': 'Invalid signature'}), 401 # Shopify will retry, but that's okay for security failure

        # 2. Idempotency Guard (Redis)
        webhook_id = request.headers.get('X-Shopify-Webhook-Id')
        if webhook_id:
            try:
                import redis
                r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
                key = f"webhook_processed:{webhook_id}"
                if r.get(key):
                    logger.info(f"Duplicate App Uninstall Webhook {webhook_id} ignored.")
                    return jsonify({'status': 'ignored_duplicate'}), 200
                r.setex(key, 86400, "1") # 24h TTL
            except Exception as re:
                logger.warning(f"Redis Idempotency Check Failed: {re}")

        # 3. Extract Data safely
        shop_domain = request.headers.get('X-Shopify-Shop-Domain', '')
        if shop_domain:
            shop_domain = shop_domain.lower().replace('https://', '').replace('http://', '').replace('www.', '').strip()
            if not shop_domain.endswith('.myshopify.com') and '.' not in shop_domain:
                shop_domain = f"{shop_domain}.myshopify.com"
        
        if not shop_domain:
            return jsonify({'error': 'Missing shop domain'}), 400

        # 4. Async Handoff
        try:
            from worker import handle_app_uninstall
            handle_app_uninstall.delay(shop_domain)
            logger.info(f"Queued async uninstall for {shop_domain}")
        except Exception as we:
            logger.error(f"Failed to queue uninstall task: {we}")
            # Fallback? No, if Redis is down, we might be in trouble, but let's return 200 to satisfy Shopify
            # or 500 to retry later. 
            # Given "Zero Downtime" goal, if queue fails, we probably WANT Shopify to retry.
            return jsonify({'error': 'Queue failed'}), 500

        return jsonify({'status': 'queued'}), 200

    except Exception as e:
        logger.error(f"Error handling app/uninstall webhook: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@webhook_shopify_bp.route('/webhooks/app_subscriptions/update', methods=['POST'])
@log_errors("WEBHOOK_ERROR")
def app_subscription_update():
    """
    Handle app subscription update webhook from Shopify - ASYNC & IDEMPOTENT
    """
    try:
        # 1. Verify Signature
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        raw_data = request.get_data(as_text=False)
        if not verify_shopify_webhook(raw_data, hmac_header):
            return jsonify({'error': 'Invalid signature'}), 401
        
        # 2. Idempotency Guard
        webhook_id = request.headers.get('X-Shopify-Webhook-Id')
        if webhook_id:
            try:
                import redis
                r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
                key = f"webhook_processed:{webhook_id}"
                if r.get(key):
                    logger.info(f"Duplicate Subscription Webhook {webhook_id} ignored.")
                    return jsonify({'status': 'ignored_duplicate'}), 200
                r.setex(key, 86400, "1")
            except Exception as re:
                logger.warning(f"Redis Idempotency Check Failed: {re}")
        
        # 3. Extract Data
        data = request.get_json()
        shop_domain = request.headers.get('X-Shopify-Shop-Domain', '')
        if shop_domain:
            shop_domain = shop_domain.lower().replace('https://', '').replace('http://', '').replace('www.', '').strip()
            if not shop_domain.endswith('.myshopify.com') and '.' not in shop_domain:
                shop_domain = f"{shop_domain}.myshopify.com"

        if not shop_domain:
            return jsonify({'error': 'Missing shop domain'}), 400

        # 4. Async Handoff
        try:
            from worker import handle_subscription_update
            handle_subscription_update.delay(shop_domain, data)
            logger.info(f"Queued async subscription update for {shop_domain}")
        except Exception as we:
            logger.error(f"Failed to queue subscription task: {we}")
            return jsonify({'error': 'Queue failed'}), 500
        
        return jsonify({'status': 'queued'}), 200
        
    except Exception as e:
        logger.error(f"Error handling app_subscriptions/update webhook: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
