"""
Shopify Billing API Integration
Replaces Stripe billing with Shopify's native billing system
"""
import os
import requests
from models import db, ShopifyStore, User
from logging_config import logger

SHOPIFY_API_VERSION = '2024-10'

class ShopifyBilling:
    def __init__(self, shop_url, access_token):
        self.shop_url = shop_url
        self.access_token = access_token
        self.api_url = f"https://{shop_url}/admin/api/{SHOPIFY_API_VERSION}"
    
    def create_usage_charge(self, description, price, currency='USD'):
        """Create a one-time usage charge"""
        url = f"{self.api_url}/recurring_application_charges.json"
        headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'recurring_application_charge': {
                'name': description,
                'price': price,
                'return_url': f"https://{os.getenv('APP_DOMAIN', 'employeesuite-production.onrender.com')}/billing/confirm"
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create usage charge: {e}")
            raise
    
    def create_recurring_charge(self, name, price, trial_days=0):
        """Create a recurring application charge (subscription)"""
        url = f"{self.api_url}/recurring_application_charges.json"
        headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'recurring_application_charge': {
                'name': name,
                'price': price,
                'return_url': f"https://{os.getenv('APP_DOMAIN', 'employeesuite-production.onrender.com')}/billing/confirm",
                'trial_days': trial_days
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            charge = data.get('recurring_application_charge', {})
            
            # Return charge ID and confirmation URL
            return {
                'charge_id': charge.get('id'),
                'confirmation_url': charge.get('confirmation_url'),
                'status': charge.get('status')
            }
        except Exception as e:
            logger.error(f"Failed to create recurring charge: {e}")
            raise
    
    def get_charge_status(self, charge_id):
        """Get the status of a charge"""
        url = f"{self.api_url}/recurring_application_charges/{charge_id}.json"
        headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            charge = data.get('recurring_application_charge', {})
            return {
                'status': charge.get('status'),
                'charge_id': charge.get('id')
            }
        except Exception as e:
            logger.error(f"Failed to get charge status: {e}")
            raise
    
    def cancel_charge(self, charge_id):
        """Cancel a recurring charge"""
        url = f"{self.api_url}/recurring_application_charges/{charge_id}.json"
        headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.delete(url, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to cancel charge: {e}")
            raise


def create_shopify_subscription(shop_url, access_token, user_id):
    """
    Create a Shopify subscription for a user
    Returns confirmation URL that user must visit
    """
    billing = ShopifyBilling(shop_url, access_token)
    
    # Create recurring charge: $500/month with 2-day trial
    result = billing.create_recurring_charge(
        name="Employee Suite Pro",
        price=500.00,
        trial_days=2
    )
    
    # Store charge_id in database
    store = ShopifyStore.query.filter_by(shop_url=shop_url, is_active=True).first()
    if store:
        store.charge_id = str(result['charge_id'])
        db.session.commit()
    
    return result['confirmation_url']


def check_subscription_status(shop_url, access_token, charge_id):
    """Check if subscription is active"""
    if not charge_id:
        return False
    
    billing = ShopifyBilling(shop_url, access_token)
    try:
        status = billing.get_charge_status(charge_id)
        return status.get('status') == 'active'
    except:
        return False
