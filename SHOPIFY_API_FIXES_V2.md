# 🔧 Shopify API Fixes V2 - December 2025

## Issues Fixed

### ✅ Error 1: GraphQL Inventory API Structure Change
**Error:** `Field 'available' doesn't exist on type 'InventoryLevel'`

**Root Cause:** Shopify changed their GraphQL API structure again. The `available` field was replaced with a `quantities` array structure.

**Fix Applied:**
- Updated GraphQL query to use `quantities(names: ["available"])` structure
- Updated response parsing to extract quantity from the array:
  ```python
  quantities = node.get("quantities", [])
  for q in quantities:
      if q.get("name") == "available":
          stock = q.get("quantity", 0)
  ```

**Files Changed:**
- `shopify_integration.py` (lines 482-488, 576-600)

---

### ✅ Error 2: MetaMask Unhandled Promise Rejections
**Error:** `Failed to connect to MetaMask from chrome-extension://...`

**Root Cause:** Browser extensions (MetaMask) inject `window.ethereum` into pages. If code tries to connect automatically, it causes unhandled promise rejections.

**Fix Applied:**
- Added safeguard to wrap `window.ethereum.request` if it exists
- Silently handle `eth_requestAccounts` rejections
- Prevents console errors from browser extensions

**Files Changed:**
- `app.py` (lines 1463-1488)

**Note:** This app does NOT use MetaMask. The safeguard prevents errors from browser extensions.

---

### ✅ Error 3: OAuth Scope Validation & 403 Errors
**Error:** `GET /admin/api/2024-10/orders.json HTTP/1.1" 403` even though scopes are granted

**Root Cause:** Scopes might be granted in OAuth but not properly configured in Shopify Partners Dashboard.

**Fix Applied:**
- Enhanced scope validation logging
- Clear error messages when scopes don't match
- Instructions to check Partners Dashboard configuration

**Files Changed:**
- `shopify_oauth.py` (lines 598-607)

**Action Required:**
1. Go to **Shopify Partners Dashboard** → Your App → **API permissions**
2. Ensure these scopes are **CHECKED** (not just requested):
   - ✅ `read_orders`
   - ✅ `read_products`
   - ✅ `read_inventory`
3. If scopes are missing, users need to disconnect and reconnect at `/settings/shopify`

---

## Verification Steps

### For Inventory API:
1. Go to dashboard
2. Click "Check Inventory" button
3. Should load inventory without GraphQL errors
4. Check server logs for any `quantities` parsing errors

### For Orders API:
1. Go to dashboard
2. Click "Process Orders" button
3. Should load orders without 403 errors
4. If 403 persists:
   - Check OAuth logs for "Granted scopes"
   - Verify Partners Dashboard has `read_orders` checked
   - Disconnect and reconnect at `/settings/shopify`

### For MetaMask Errors:
1. Open browser console
2. Should NOT see "Failed to connect to MetaMask" errors
3. Any MetaMask errors should be silently handled

---

## Deployment Status

- ✅ GraphQL quantities structure: Committed and pushed
- ✅ MetaMask safeguard: Committed and pushed
- ✅ Enhanced scope validation: Committed and pushed
- ⚠️ User action required: Partners Dashboard scope configuration

---

## Important Notes

1. **GraphQL API Changes:** Shopify frequently updates their API. The `quantities` structure is the current format.

2. **MetaMask:** This is NOT a crypto app. MetaMask errors are from browser extensions, not our code. The safeguard prevents console noise.

3. **OAuth Scopes:** Even if OAuth grants scopes, the Partners Dashboard must have them checked. This is a Shopify requirement.

4. **Reconnection Required:** Users with 403 errors must disconnect and reconnect to get updated scopes from Partners Dashboard.


