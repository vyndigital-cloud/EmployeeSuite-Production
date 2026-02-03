from flask import Blueprint, request, jsonify
import stripe
import os
from models import db, User
from email_service import send_payment_failed
from logging_config import logger

webhook_bp = Blueprint('webhook', __name__)

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

@webhook_bp.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle different event types
    event_type = event['type']
    data = event['data']['object']
    
    logger.info(f"Received Stripe webhook: {event_type}")
    
    if event_type == 'invoice.payment_failed':
        handle_payment_failed(data)
    
    elif event_type == 'invoice.payment_succeeded':
        handle_payment_succeeded(data)
    
    elif event_type == 'customer.subscription.deleted':
        handle_subscription_deleted(data)
    
    elif event_type == 'customer.subscription.updated':
        handle_subscription_updated(data)
    
    return jsonify({'status': 'success'}), 200

def handle_payment_failed(invoice):
    """Handle failed payment - lock user out"""
    customer_id = invoice.get('customer')
    
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        logger.warning(f"User not found for customer {customer_id}")
        return
    
    # Lock user out
    user.is_subscribed = False
    db.session.commit()
    
    # Send email notification
    try:
        send_payment_failed(user.email)
    except Exception as e:
        logger.error(f"Failed to send payment failed email: {e}")
    
    logger.warning(f"Payment failed for {user.email} - access revoked")

def handle_payment_succeeded(invoice):
    """Handle successful payment - ensure user has access"""
    customer_id = invoice.get('customer')
    
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        logger.warning(f"User not found for customer {customer_id}")
        return
    
    # Ensure user is marked as subscribed
    if not user.is_subscribed:
        user.is_subscribed = True
        db.session.commit()
        logger.info(f"Payment succeeded for {user.email} - access granted")

def handle_subscription_deleted(subscription):
    """Handle subscription cancellation from Stripe dashboard"""
    customer_id = subscription.get('customer')
    
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        logger.warning(f"User not found for customer {customer_id}")
        return
    
    # Revoke access
    user.is_subscribed = False
    db.session.commit()
    
    logger.info(f"Subscription deleted for {user.email} - access revoked")

def handle_subscription_updated(subscription):
    """Handle subscription updates (plan changes, etc)"""
    customer_id = subscription.get('customer')
    status = subscription.get('status')
    
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        logger.warning(f"User not found for customer {customer_id}")
        return
    
    # Update subscription status based on Stripe status
    if status in ['active', 'trialing']:
        user.is_subscribed = True
    else:
        user.is_subscribed = False
    
    db.session.commit()
    logger.info(f"Subscription updated for {user.email} - status: {status}")
