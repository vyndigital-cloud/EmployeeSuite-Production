# Clear Store Token - Manual Fix

If you're experiencing a loop where the app keeps trying to use an old access token, you need to manually clear it from the database.

## Option 1: Use the Python Script (Recommended)

```bash
python clear_store_token.py testsuite-dev.myshopify.com
```

This script will:
1. Find the store in the database
2. Use the `disconnect()` method to properly clear the token
3. Verify the token is cleared
4. Show you the current state

## Option 2: Direct Database Query

If you have direct database access, you can run:

```sql
-- Clear just the access_token
UPDATE shopify_stores 
SET access_token = '', is_active = false 
WHERE shop_url = 'testsuite-dev.myshopify.com';

-- Or delete the entire record
DELETE FROM shopify_stores 
WHERE shop_url = 'testsuite-dev.myshopify.com';
```

## Option 3: Use the Settings Page

1. Go to `/settings/shopify` in your app
2. Click "Disconnect Store"
3. This will call `store.disconnect()` and clear the token

## After Clearing the Token

1. **Uninstall the app from Shopify Admin:**
   - Go to Shopify Admin → Apps → Your App → Uninstall

2. **Reinstall using OAuth:**
   - Use the "Connect with Shopify" button in your app settings
   - OR visit: `/install?shop=testsuite-dev.myshopify.com`
   - This will generate a NEW access token from your Partners app

## Why This Happens

When you switch from a custom app to a Partners app:
- The old access token is tied to the old app
- Shopify won't accept it for billing operations
- The code detects this and tries to redirect to OAuth
- But if the token is still in the database, it keeps looping

**Solution:** Clear the old token, then reinstall via OAuth to get a new Partners app token.
