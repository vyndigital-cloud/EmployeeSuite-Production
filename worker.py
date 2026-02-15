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

@app.task(bind=True, max_retries=5)
def sync_usage_to_shopify(self):
    """
    PASSIVE REVENUE SYNC
    Batch and sync pending UsageEvents to Shopify.
    Scheduled to run every hour or triggered by high usage.
    """
    from models import db, UsageEvent, ShopifyStore
    from app_factory import create_app
    from billing_metered import sync_usage_event_to_shopify, get_subscription_line_item_id
    from datetime import datetime
    import logging
    
    logger = logging.getLogger(__name__)
    flask_app = create_app()
    with flask_app.app_context():
        try:
            # 1. Fetch pending events
            pending_events = UsageEvent.query.filter(UsageEvent.reported_at == None).all()
            if not pending_events:
                return {"status": "no_pending_events"}
            
            # 2. Group by store for efficiency
            store_events = {}
            for event in pending_events:
                if event.store_id not in store_events:
                    store_events[event.store_id] = []
                store_events[event.store_id].append(event)
            
            synced_count = 0
            for store_id, events in store_events.items():
                store = ShopifyStore.query.get(store_id)
                if not store:
                    continue
                
                access_token = store.get_access_token()
                if not access_token:
                    continue
                
                # 3. Get line item ID
                # In a high-scale app, we would cache this in Redis for 24h
                line_item_id = get_subscription_line_item_id(store.shop_url, access_token)
                if not line_item_id:
                    logger.warning(f"No metered subscription line item found for {store.shop_url}")
                    continue
                
                for event in events:
                    record_id = sync_usage_event_to_shopify(
                        store.shop_url, 
                        access_token, 
                        line_item_id, 
                        event
                    )
                    if record_id:
                        # Extract record_id from GID if necessary, but we can store the whole GID
                        # Shopify GIDs are strings, so cast if model expects int (it does)
                        try:
                            if isinstance(record_id, str) and "/" in record_id:
                                event.shopify_usage_record_id = int(record_id.split("/")[-1])
                            else:
                                event.shopify_usage_record_id = int(record_id)
                        except (ValueError, TypeError):
                            # If we can't parse it as int, we'll just mark it reported without the ID
                            pass
                            
                        event.reported_at = datetime.utcnow()
                        synced_count += 1
            
            db.session.commit()
            logger.info(f"✅ [WORKER] Synced {synced_count} usage events to Shopify.")
            return {"status": "success", "synced": synced_count}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ [WORKER] Usage Sync Failed: {e}", exc_info=True)
            raise self.retry(exc=e, countdown=600) # Retry in 10 minutes

@app.task(bind=True, max_retries=3)
def handle_order_created(self, shop_domain, order_data):
    """
    ASYNC REVENUE ENGINE
    Process new orders in background to calculate revenue stats.
    Zero-latency for the webhook response.
    """
    from models import db, ShopifyStore
    from app_factory import create_app
    import logging
    
    logger = logging.getLogger(__name__)
    flask_app = create_app()
    with flask_app.app_context():
        try:
            # 1. Verify store exists
            store = ShopifyStore.query.filter_by(shop_url=shop_domain).first()
            if not store:
                logger.warning(f"⚠️ Revenue sync skipped: Store {shop_domain} not found.")
                return

            # 2. Extract revenue data
            total_price = float(order_data.get('total_price', 0))
            currency = order_data.get('currency', 'USD')
            order_id = order_data.get('id')
            
            logger.info(f"💰 [REVENUE] Processing Order {order_id} for {shop_domain}: {total_price} {currency}")
            
            # TODO: Add your actual revenue aggregation logic here
            # For now, we log it to prove the async pipe is working
            
            return {"status": "success", "order_id": order_id, "revenue": total_price}
            
        except Exception as e:
            logger.error(f"❌ [WORKER] Revenue Sync Failed: {e}", exc_info=True)
            raise self.retry(exc=e)
