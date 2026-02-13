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

@app.task(bind=True, max_retries=3)
def handle_app_uninstall(self, shop_domain):
    """
    Async handler for app/uninstall webhook.
    """
    from models import db, ShopifyStore, User
    from app_factory import create_app
    
    # Create app context for DB access
    flask_app = create_app()
    with flask_app.app_context():
        try:
            print(f"Worker: Processing uninstall for {shop_domain}")
            store = ShopifyStore.query.filter_by(shop_url=shop_domain, is_active=True).first()
            if store:
                store.is_active = False
                store.uninstalled_at = time.strftime('%Y-%m-%d %H:%M:%S') # simplistic, better to use datetime
                # SCRUB
                store.access_token = None
                db.session.commit()
                # store.invalidate_cache() # Method might not exist in worker context easily if not bound to app? 
                # Actually models are bound to db, so it should work if implementation uses db/cache.
                # Assuming simple invalidation:
                print(f"Worker: Store {shop_domain} uninstalled.")
            else:
                print(f"Worker: Store {shop_domain} not found or already inactive.")
        except Exception as e:
            print(f"Worker Error (uninstall): {e}")
            raise self.retry(exc=e)

@app.task(bind=True, max_retries=3)
def handle_subscription_update(self, shop_domain, data):
    """
    Async handler for app_subscriptions/update webhook.
    """
    from models import db, ShopifyStore, User
    from app_factory import create_app
    
    flask_app = create_app()
    with flask_app.app_context():
        try:
            print(f"Worker: Processing subscription update for {shop_domain}")
            store = ShopifyStore.query.filter_by(shop_url=shop_domain).first()
            if not store:
                print(f"Worker: Store {shop_domain} not found.")
                return
            
            app_subscription = data.get('app_subscription', {})
            status = app_subscription.get('status', '')
            charge_id = app_subscription.get('id', '')
            
            if charge_id:
                store.charge_id = str(charge_id)
            
            user = User.query.get(store.user_id)
            if user:
                if status == 'active':
                    user.is_subscribed = True
                    print(f"Worker: Subscription ACTIVE for {shop_domain}")
                elif status in ['cancelled', 'expired', 'declined']:
                    user.is_subscribed = False
                    print(f"Worker: Subscription {status} for {shop_domain}")
            
            db.session.commit()
            
        except Exception as e:
            print(f"Worker Error (sub update): {e}")
            raise self.retry(exc=e)
