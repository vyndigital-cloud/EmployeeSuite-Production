"""
Shopify Billing API Integration - Production Ready
Implements proper Shopify Billing API for embedded apps
Required for Shopify App Store compliance
"""
import json
import logging
import requests
import os
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, Response, url_for
from models import db, ShopifyStore, User
from logging_config import logger

billing_bp = Blueprint('shopify_billing', __name__)

# Billing plans configuration
BILLING_PLANS = {
    'growth': {
        'name': 'Growth Plan',
        'price': 99.00,
        'interval': 'EVERY_30_DAYS',
        'features': [
            'Inventory Intelligence Dashboard',
            'Smart Reorder Recommendations', 
            'Dead Stock Alerts',
            '30-Day Sales Forecasting',
            'CSV Export Capable',
            'Up to 3 Store Connections',
            'Email Support'
        ],
        'trial_days': 7
    },
    'scale': {
        'name': 'Scale Plan', 
        'price': 297.00,
        'interval': 'EVERY_30_DAYS',
        'features': [
            'Everything in Growth',
            'Advanced Multi-Location Sync',
            'Automated Supplier Emails',
            'Custom Reporting Engine',
            'Unlimited Data History',
            'Priority 24/7 Support',
            'Dedicated Success Manager',
            'Early Access to Beta Features'
        ],
        'trial_days': 14
    }
}

def create_shopify_billing_request(shop_domain, plan_id, return_url):
    """
    Create a Shopify billing request
    Returns billing URL for redirect
    """
    try:
        store = ShopifyStore.query.filter_by(shop_domain=shop_domain).first()
        if not store or not store.access_token:
            logger.error(f"Store not found or no access token for {shop_domain}")
            return None
        
        plan = BILLING_PLANS.get(plan_id)
        if not plan:
            logger.error(f"Invalid plan ID: {plan_id}")
            return None
        
        # Create recurring application charge via Shopify API
        url = f"https://{shop_domain}/admin/api/2025-10/recurring_application_charges.json"
        
        headers = {
            'X-Shopify-Access-Token': store.access_token,
            'Content-Type': 'application/json'
        }
        
        charge_data = {
            "recurring_application_charge": {
                "name": plan['name'],
                "price": str(plan['price']),
                "return_url": return_url,
                "trial_days": plan['trial_days'],
                "test": os.getenv('ENVIRONMENT') != 'production'
            }
        }
        
        response = requests.post(url, json=charge_data, headers=headers)
        
        if response.status_code == 201:
            charge = response.json().get('recurring_application_charge')
            logger.info(f"Created billing charge for {shop_domain}: {charge.get('id')}")
            return charge.get('confirmation_url')
        else:
            logger.error(f"Failed to create billing charge: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error creating billing request: {e}")
        return None

def activate_billing_charge(shop_domain, charge_id):
    """
    Activate a billing charge after merchant confirmation
    """
    try:
        store = ShopifyStore.query.filter_by(shop_domain=shop_domain).first()
        if not store or not store.access_token:
            return False
        
        url = f"https://{shop_domain}/admin/api/2025-10/recurring_application_charges/{charge_id}/activate.json"
        
        headers = {
            'X-Shopify-Access-Token': store.access_token,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, headers=headers)
        
        if response.status_code == 200:
            charge = response.json().get('recurring_application_charge')
            
            # Update store subscription info
            store.is_subscribed = True
            store.subscription_plan = charge.get('name')
            store.subscription_price = float(charge.get('price'))
            store.subscription_id = charge.get('id')
            store.subscription_status = charge.get('status')
            store.billing_on = datetime.fromisoformat(charge.get('billing_on').replace('Z', '+00:00')) if charge.get('billing_on') else None
            store.trial_ends_at = datetime.fromisoformat(charge.get('trial_ends_on').replace('Z', '+00:00')) if charge.get('trial_ends_on') else None
            
            db.session.commit()
            
            logger.info(f"Activated billing for {shop_domain}: {charge.get('id')}")
            return True
        else:
            logger.error(f"Failed to activate billing: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error activating billing charge: {e}")
        return False

def check_billing_status(shop_domain):
    """
    Check current billing status for a shop
    """
    try:
        store = ShopifyStore.query.filter_by(shop_domain=shop_domain).first()
        if not store:
            return None
        
        # Check if subscription is active
        if store.is_subscribed and store.subscription_id:
            # Verify with Shopify API
            url = f"https://{shop_domain}/admin/api/2025-10/recurring_application_charges/{store.subscription_id}.json"
            
            headers = {
                'X-Shopify-Access-Token': store.access_token
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                charge = response.json().get('recurring_application_charge')
                
                # Update local status
                store.subscription_status = charge.get('status')
                store.billing_on = datetime.fromisoformat(charge.get('billing_on').replace('Z', '+00:00')) if charge.get('billing_on') else None
                
                db.session.commit()
                
                return {
                    'active': charge.get('status') == 'active',
                    'plan': store.subscription_plan,
                    'price': store.subscription_price,
                    'trial_ends': store.trial_ends_at.isoformat() if store.trial_ends_at else None,
                    'billing_on': store.billing_on.isoformat() if store.billing_on else None
                }
        
        # Check trial status
        if store.trial_ends_at and store.trial_ends_at > datetime.utcnow():
            return {
                'active': True,
                'trial': True,
                'trial_ends': store.trial_ends_at.isoformat(),
                'days_left': (store.trial_ends_at - datetime.utcnow()).days
            }
        
        return {'active': False}
        
    except Exception as e:
        logger.error(f"Error checking billing status: {e}")
        return None

def cancel_subscription(shop_domain):
    """
    Cancel shop's subscription
    """
    try:
        store = ShopifyStore.query.filter_by(shop_domain=shop_domain).first()
        if not store or not store.subscription_id:
            return False
        
        # Delete charge in Shopify
        url = f"https://{shop_domain}/admin/api/2025-10/recurring_application_charges/{store.subscription_id}.json"
        
        headers = {
            'X-Shopify-Access-Token': store.access_token
        }
        
        response = requests.delete(url, headers=headers)
        
        if response.status_code == 200:
            # Update local records
            store.is_subscribed = False
            store.subscription_status = 'cancelled'
            store.cancelled_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Cancelled subscription for {shop_domain}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        return False

@billing_bp.route('/api/billing/plans', methods=['GET'])
def get_billing_plans():
    """
    Get available billing plans
    """
    try:
        shop = request.args.get('shop')
        if not shop:
            return jsonify({'error': 'Missing shop parameter'}), 400
        
        # Get current billing status
        status = check_billing_status(shop)
        
        return jsonify({
            'plans': BILLING_PLANS,
            'current_status': status,
            'shop': shop
        })
        
    except Exception as e:
        logger.error(f"Error getting billing plans: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@billing_bp.route('/api/billing/subscribe', methods=['POST'])
def subscribe_to_plan():
    """
    Subscribe to a billing plan
    """
    try:
        data = request.get_json()
        shop = data.get('shop')
        plan_id = data.get('plan_id')
        
        if not shop or not plan_id:
            return jsonify({'error': 'Missing shop or plan_id'}), 400
        
        # Create return URL
        return_url = url_for('shopify_billing.billing_callback', 
                           shop=shop, plan_id=plan_id, _external=True)
        
        # Create billing request
        billing_url = create_shopify_billing_request(shop, plan_id, return_url)
        
        if not billing_url:
            return jsonify({'error': 'Failed to create billing request'}), 500
        
        return jsonify({
            'success': True,
            'billing_url': billing_url
        })
        
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@billing_bp.route('/billing/callback', methods=['GET'])
def billing_callback():
    """
    Handle billing callback from Shopify
    """
    try:
        shop = request.args.get('shop')
        plan_id = request.args.get('plan_id')
        charge_id = request.args.get('charge_id')
        
        if not shop or not charge_id:
            return "Missing required parameters", 400
        
        # Activate the charge
        if activate_billing_charge(shop, charge_id):
            # Redirect to success page
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Billing Successful - Employee Suite</title>
                <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
            </head>
            <body>
                <div style="text-align: center; padding: 50px; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                    <h2>✅ Billing Successful</h2>
                    <p>Your subscription has been activated. Redirecting to dashboard...</p>
                </div>
                <script>
                    if (window.shopify && window.shopify.app) {{
                        window.shopify.app.dispatch(window.shopify.app.Action.REDIRECT, {{
                            path: '/dashboard'
                        }});
                    }} else {{
                        window.location.href = '/dashboard?shop={shop}';
                    }}
                </script>
            </body>
            </html>
            """
        else:
            return "Failed to activate billing", 500
            
    except Exception as e:
        logger.error(f"Error in billing callback: {e}")
        return "Internal server error", 500

@billing_bp.route('/api/billing/status', methods=['GET'])
def get_billing_status():
    """
    Get current billing status
    """
    try:
        shop = request.args.get('shop')
        if not shop:
            return jsonify({'error': 'Missing shop parameter'}), 400
        
        status = check_billing_status(shop)
        
        if not status:
            return jsonify({'error': 'Failed to check billing status'}), 500
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting billing status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@billing_bp.route('/api/billing/cancel', methods=['POST'])
def cancel_billing():
    """
    Cancel current subscription
    """
    try:
        data = request.get_json()
        shop = data.get('shop')
        
        if not shop:
            return jsonify({'error': 'Missing shop parameter'}), 400
        
        if cancel_subscription(shop):
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to cancel subscription'}), 500
            
    except Exception as e:
        logger.error(f"Error cancelling billing: {e}")
        return jsonify({'error': 'Internal server error'}), 500
