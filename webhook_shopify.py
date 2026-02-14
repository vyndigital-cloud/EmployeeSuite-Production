"""
Shopify Webhook Handlers for App Store
Handles app/uninstall and app_subscriptions/update webhooks
"""
from flask import Blueprint, request, jsonify, g
import hmac
import hashlib
import base64
import os
import redis
from functools import wraps
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

def shopify_webhook_verified(f):
    """Decorator to verify Shopify webhook HMAC signature"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        raw_data = request.get_data(as_text=False)
        
        if not verify_shopify_webhook(raw_data, hmac_header):
            logger.warning(f"🚫 Webhook Verify Fail: {request.path}")
            return jsonify({'error': 'Unauthorized'}), 401
            
        # Context Injection
        shop_domain_header = request.headers.get('X-Shopify-Shop-Domain')
        if shop_domain_header:
            # Normalize shop domain
            normalized_shop_domain = shop_domain_header.lower().replace('https://', '').replace('http://', '').replace('www.', '').strip()
            if not normalized_shop_domain.endswith('.myshopify.com') and '.' not in normalized_shop_domain:
                normalized_shop_domain = f"{normalized_shop_domain}.myshopify.com"
            request.webhook_shop = normalized_shop_domain
            
        return f(*args, **kwargs)
    return decorated_function

def idempotency_guard(ttl=86400):
    """Decorator to prevent duplicate webhook processing using Redis"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            webhook_id = request.headers.get('X-Shopify-Webhook-Id')
            if not webhook_id:
                # If no webhook ID, proceed without idempotency check
                logger.warning(f"Webhook received without X-Shopify-Webhook-Id: {request.path}")
                return f(*args, **kwargs)
            
            try:
                r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
                key = f"webhook_processed:{webhook_id}"
                # Bulletproof setnx: atomic check and set
                if r.setnx(key, "1"):
                    r.expire(key, ttl)
                else:
                    logger.info(f"🔄 Duplicate Webhook Ignored: {webhook_id} for {request.path}")
                    return jsonify({'status': 'ignored_duplicate'}), 200
            except Exception as re:
                logger.error(f"⚠️ Redis Idempotency Error for webhook {webhook_id}: {re}", exc_info=True)
                # Fail safe: if Redis is down, we allow the request to proceed.
                # This means potential duplicate processing, but avoids blocking webhooks entirely.
                # Shopify will retry if we return 5xx, so allowing it to proceed and potentially
                # process twice is better than blocking all webhooks.
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@webhook_shopify_bp.route('/webhooks/app/uninstall', methods=['POST'])
@log_errors("WEBHOOK_ERROR")
@shopify_webhook_verified
@idempotency_guard()
def app_uninstall():
    """
    Handle app uninstall webhook - WORKER-FIRST
    """
    shop_domain = getattr(request, 'webhook_shop', None)
    if not shop_domain:
        logger.error("Missing shop domain after verification for app/uninstall webhook.")
        return jsonify({'error': 'Missing shop domain'}), 400

    try:
        from worker import handle_app_uninstall
        handle_app_uninstall.delay(shop_domain)
        logger.info(f"🚀 Queued async uninstall for {shop_domain}")
    except Exception as we:
        logger.error(f"❌ Worker Handoff Failed for app/uninstall ({shop_domain}): {we}", exc_info=True)
        return jsonify({'error': 'Queue failed'}), 500

    return jsonify({'status': 'queued'}), 200

@webhook_shopify_bp.route('/webhooks/app_subscriptions/update', methods=['POST'])
@log_errors("WEBHOOK_ERROR")
@shopify_webhook_verified
@idempotency_guard()
def app_subscription_update():
    """
    Handle app subscription update webhook - WORKER-FIRST
    """
    shop_domain = getattr(request, 'webhook_shop', None)
    data = request.get_json()
    
    if not shop_domain:
        logger.error("Missing shop domain after verification for app_subscriptions/update webhook.")
        return jsonify({'error': 'Missing shop domain'}), 400

    try:
        from worker import handle_subscription_update
        handle_subscription_update.delay(shop_domain, data)
        logger.info(f"🚀 Queued async subscription update for {shop_domain}")
    except Exception as we:
        logger.error(f"❌ Worker Handoff Failed for app_subscriptions/update ({shop_domain}): {we}", exc_info=True)
        return jsonify({'error': 'Queue failed'}), 500
    
    return jsonify({'status': 'queued'}), 200
