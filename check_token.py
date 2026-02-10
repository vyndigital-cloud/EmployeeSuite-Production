from models import db, ShopifyStore
from app_factory import create_app
import os

app = create_app()
with app.app_context():
    store = ShopifyStore.query.filter_by(shop_url='employee-suite.myshopify.com').first()
    if store:
        print(f"SHOP_FOUND: True")
        print(f"TOKEN_PREVIEW: {store.access_token[:25]}")
        print(f"TOKEN_LENGTH: {len(store.access_token)}")
    else:
        print(f"SHOP_FOUND: False")
