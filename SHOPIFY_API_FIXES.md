# 🔧 Shopify API Fixes - December 2025

## Issues Fixed

### ✅ Error 1: Inventory API GraphQL Field
**Error:** `Field 'quantityAvailable' doesn't exist on type 'InventoryLevel'`

**Root Cause:** Shopify changed their GraphQL API. The field `quantityAvailable` was renamed to `available`.

**Fix Applied:**
- Updated GraphQL query in `shopify_integration.py`:
  - Changed `quantityAvailable` → `available` in the query
  - Updated response parsing to use `available` field

**Files Changed:**
- `shopify_integration.py` (lines 485, 587)

---

### ✅ Error 2: Orders API 403 Forbidden
**Error:** `GET /admin/api/2024-10/orders.json?financial_status=pending&limit=250 HTTP/1.1" 403`

**Root Cause:** The app is missing the `read_orders` scope. Users who connected before the scopes were added need to reconnect.

**Current Scopes (Already Configured):**
- ✅ `read_products` - Required for product data
- ✅ `read_inventory` - Required for inventory levels
- ✅ `read_orders` - Required for order data

**Scopes are correctly defined in:**
- `shopify_oauth.py` line 23: `SCOPES = 'read_products,read_inventory,read_orders'`
- `shopify.app.toml` line 10: `scopes = "read_inventory,read_orders,read_products"`

**Action Required:**
Users who are getting 403 errors need to:
1. Go to `/settings/shopify`
2. Click "Disconnect Store"
3. Click "Connect with Shopify" to reconnect with the new scopes

---

## Verification Steps

### For Inventory API:
1. Go to dashboard
2. Click "Check Inventory" button
3. Should load inventory without GraphQL errors

### For Orders API:
1. Go to dashboard
2. Click "Process Orders" button
3. Should load orders without 403 errors
4. If you get 403, disconnect and reconnect at `/settings/shopify`

---

## Deployment Status

- ✅ GraphQL field fix: Committed and pushed
- ✅ Scopes: Already configured correctly
- ⚠️ User action required: Users with 403 errors need to reconnect

---

## Notes

- The scopes are already correctly configured in the code
- Users who connected before these scopes were added need to reconnect
- The disconnect/reconnect flow is already implemented in the settings page
- No code changes needed for scopes - they're already correct


