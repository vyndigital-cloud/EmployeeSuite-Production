import os
from celery import Celery
import time

# Initialize Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app = Celery('missioncontrol_tasks', broker=REDIS_URL, backend=REDIS_URL)

# Legend Tier Resilience: Optimal configuration for Shopify API
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # Shopify Leaky Bucket: 2 requests per second for REST
    # We set a slightly lower limit to be safe for a single worker
    task_annotations={
        '*': {'rate_limit': '2/s'}
    }
)

@app.task(bind=True, max_retries=5, default_retry_delay=300)
def shopify_api_call(self, shop_domain, action, params=None):
    """
    Resilient Shopify API task with exponential backoff for 429s.
    """
    from models import ShopifyStore
    from shopify_integration import ShopifyClient
    
    try:
        store = ShopifyStore.query.filter_by(shop_url=shop_domain).first()
        if not store or not store.access_token:
            return {"error": "Store or token missing", "shop": shop_domain}
            
        client = ShopifyClient(shop_domain, store.access_token)
        
        # Example action: sync_inventory
        if action == "sync_inventory":
            # Implementation here...
            pass
            
        return {"status": "success", "shop": shop_domain, "action": action}
        
    except Exception as exc:
        # Check if it's a 429 Too Many Requests
        if "429" in str(exc):
            print(f"🚨 Rate limit hit for {shop_domain}. Retrying...")
            # Exponential backoff (already assisted by Celery's default_retry_delay)
            raise self.retry(exc=exc, countdown=min(2**self.request.retries * 300, 3600))
        
        print(f"⚠️ Task failed for {shop_domain}: {exc}")
        raise exc
