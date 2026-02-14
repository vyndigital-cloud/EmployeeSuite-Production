"""
Shopify Metered Billing Integration
Handles syncing UsageEvents with the appUsageRecordCreate GraphQL mutation.
"""
import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def sync_usage_event_to_shopify(shop_url: str, access_token: str, subscription_line_item_id: str, usage_event: Any) -> Optional[str]:
    """
    Push a single UsageEvent to Shopify's Billing API.
    Returns the Shopify UsageRecord ID on success, None otherwise.
    """
    mutation = """
    mutation appUsageRecordCreate($description: String!, $price: MoneyInput!, $subscriptionLineItemId: ID!, $idempotencyKey: String!) {
      appUsageRecordCreate(description: $description, price: $price, subscriptionLineItemId: $subscriptionLineItemId, idempotencyKey: $idempotencyKey) {
        appUsageRecord {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {
        "description": usage_event.description or f"Usage: {usage_event.event_type}",
        "price": {
            "amount": float(usage_event.price),
            "currencyCode": "USD"
        },
        "subscriptionLineItemId": subscription_line_item_id,
        "idempotencyKey": usage_event.idempotency_key
    }
    
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    url = f"https://{shop_url}/admin/api/2024-04/graphql.json"
    
    try:
        response = requests.post(url, json={"query": mutation, "variables": variables}, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        data = result.get("data", {}).get("appUsageRecordCreate", {})
        
        user_errors = data.get("userErrors", [])
        if user_errors:
            for error in user_errors:
                logger.error(f"Shopify Billing Error ({shop_url}): {error['field']} - {error['message']}")
            return None
            
        record_id = data.get("appUsageRecord", {}).get("id")
        if record_id:
            logger.info(f"✅ [BILLING] Synced {usage_event.event_type} to Shopify: {record_id}")
            return record_id
            
        return None
        
    except Exception as e:
        logger.error(f"❌ [BILLING] Sync Connection Failed for {shop_url}: {e}")
        return None

def get_subscription_line_item_id(shop_url: str, access_token: str) -> Optional[str]:
    """
    Fetch the active subscription's metered line item ID.
    Required for pushing usage records.
    """
    query = """
    {
      currentAppInstallation {
        activeSubscriptions {
          id
          lineItems {
            id
            plan {
              pricingDetails {
                __typename
                ... on AppUsagePricing {
                  terms
                }
              }
            }
          }
        }
      }
    }
    """
    
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    url = f"https://{shop_url}/admin/api/2024-04/graphql.json"
    
    try:
        response = requests.post(url, json={"query": query}, headers=headers)
        response.raise_for_status()
        
        data = response.json().get("data", {}).get("currentAppInstallation", {})
        subscriptions = data.get("activeSubscriptions", [])
        
        for sub in subscriptions:
            for item in sub.get("lineItems", []):
                # We look for the usage-based pricing line item
                pricing = item.get("plan", {}).get("pricingDetails", {})
                if pricing.get("__typename") == "AppUsagePricing":
                    return item["id"]
                    
        return None
    except Exception as e:
        logger.error(f"Failed to fetch subscription line item for {shop_url}: {e}")
        return None
