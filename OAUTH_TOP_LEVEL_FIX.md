# ✅ Fixed: OAuth Redirect "accounts.shopify.com refused to connect"

## Problem

When users clicked "Connect with Shopify" from within an embedded app (iframe), the OAuth flow would attempt to redirect to `accounts.shopify.com` inside the iframe. However, Shopify sets `X-Frame-Options: deny` on their accounts page, causing the error:

```
accounts.shopify.com refused to connect
```

## Root Cause

- OAuth must happen in a **top-level window**, not in an iframe
- Shopify's OAuth flow redirects to `accounts.shopify.com` for authentication
- `accounts.shopify.com` has `X-Frame-Options: deny` header
- When OAuth was triggered from within an embedded app, it tried to load in the iframe
- Browser blocked it due to X-Frame-Options

## Solution

Modified `/install` endpoint (`shopify_oauth.py`) to:

1. **Detect embedded context**: Check if `host` parameter is present (indicates embedded app)
2. **Use App Bridge Redirect**: If embedded, render an HTML page that uses App Bridge's `Redirect.Action.REMOTE` to open OAuth in the **top-level window**
3. **Fallback**: If App Bridge fails, use `window.top.location.href` as a fallback
4. **Non-embedded**: Regular redirect works fine for standalone access

## Changes Made

### 1. `shopify_oauth.py` - `/install` route
- Added detection for embedded context (`host` parameter)
- When embedded, renders HTML page with App Bridge Redirect
- Uses `Redirect.Action.REMOTE` to navigate top-level window to OAuth URL
- Regular redirect for non-embedded installations

### 2. `shopify_routes.py` - Settings page form
- Added hidden `host` input field that passes `host` parameter to `/install` route
- Only included if `host` is present in current URL (embedded context)

## How It Works Now

1. **Embedded App Flow**:
   - User clicks "Connect with Shopify" from settings page
   - Form submits to `/install?shop=...&host=...`
   - `/install` detects `host` parameter
   - Renders HTML page with App Bridge script
   - App Bridge redirects **top-level window** to OAuth URL
   - OAuth completes in top-level window ✅
   - Redirects back to app callback

2. **Non-Embedded Flow**:
   - User clicks "Connect with Shopify" from standalone page
   - Form submits to `/install?shop=...`
   - `/install` redirects directly to OAuth URL
   - OAuth completes normally ✅

## Testing

✅ **Test embedded OAuth**:
1. Open app in Shopify admin (embedded iframe)
2. Go to Settings → Connect Shopify Store
3. Enter shop domain and click "Connect with Shopify"
4. Should redirect to OAuth in **top-level window** (not iframe)
5. Complete OAuth flow
6. Should redirect back to app

✅ **Test standalone OAuth**:
1. Open app in standalone window (not embedded)
2. Go to Settings → Connect Shopify Store
3. Enter shop domain and click "Connect with Shopify"
4. Should redirect to OAuth normally
5. Complete OAuth flow
6. Should redirect back to app

## Result

- ✅ No more "accounts.shopify.com refused to connect" errors
- ✅ OAuth works correctly in embedded apps
- ✅ OAuth works correctly in standalone access
- ✅ App Bridge properly handles top-level navigation

