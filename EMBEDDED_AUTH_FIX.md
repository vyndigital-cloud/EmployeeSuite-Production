# 🔧 Embedded App Authentication Fix

## Problem

The app was showing a manual login form for embedded apps, which violates Shopify's embedded app requirements. Embedded apps must use Shopify's OAuth flow, not a separate email/password login.

## Root Cause

1. **Login route** was showing a login form even for embedded apps
2. **Unauthorized handler** was redirecting embedded apps to the login form
3. **Dashboard route** was trying to auto-login embedded apps instead of redirecting to OAuth

## Solution

### 1. Fixed Login Route (`auth.py`)

**Before:** Showed login form for all requests (including embedded)

**After:** 
- Detects if request is embedded (has `shop` and/or `host` params)
- If embedded, redirects to OAuth install flow instead of showing login form
- Only shows login form for standalone (non-embedded) access

```python
# CRITICAL: For embedded apps, use Shopify OAuth flow - NO login form
is_embedded = embedded == '1' or host or shop
if is_embedded and shop:
    install_url = url_for('oauth.install', shop=shop, host=host) if host else url_for('oauth.install', shop=shop)
    return redirect(install_url)
```

### 2. Fixed Unauthorized Handler (`app.py`)

**Before:** Redirected all unauthorized requests (including embedded) to login form

**After:**
- Detects if request is embedded
- If embedded, redirects to OAuth install flow
- Only redirects to login form for standalone access

```python
# CRITICAL: For embedded apps, redirect to OAuth (Shopify's embedded auth flow)
# DO NOT redirect to login form - embedded apps use OAuth
if embedded == '1' or (shop and host):
    if shop:
        install_url = url_for('oauth.install', shop=shop, host=host) if host else url_for('oauth.install', shop=shop)
        return redirect(install_url)
```

### 3. Fixed Dashboard Route (`app.py`)

**Before:** Tried to auto-login embedded apps when no session found

**After:**
- Checks if store exists and is connected
- If no active store found, redirects to OAuth install flow
- Properly uses `store.is_connected()` method

```python
# If embedded but no session/store found, redirect to OAuth
if is_embedded and shop and not current_user.is_authenticated:
    store = ShopifyStore.query.filter_by(shop_url=shop, is_active=True).first()
    if not store or not store.is_connected():
        install_url = url_for('oauth.install', shop=shop, host=host) if host else url_for('oauth.install', shop=shop)
        return redirect(install_url)
```

## How It Works Now

### Embedded App Flow (Shopify Admin)

1. User opens app in Shopify admin (iframe loads with `shop` and `host` params)
2. App checks if store is connected
3. **If not connected:** Redirects to `/install?shop=...&host=...` (OAuth flow)
4. OAuth flow:
   - Redirects to Shopify OAuth approval (top-level redirect)
   - User approves
   - Callback creates/updates store and user
   - Redirects back to dashboard in iframe
5. App Bridge handles session tokens for all API calls

### Standalone Flow (Direct Access)

1. User visits app URL directly (no `shop`/`host` params)
2. App redirects to `/login` (login form)
3. User enters email/password
4. Flask-Login creates session cookie
5. Redirects to dashboard

## Benefits

✅ **Compliant with Shopify requirements** - Embedded apps use OAuth, not login forms  
✅ **No cross-origin cookie issues** - Session tokens handle auth in iframes  
✅ **Proper top-level redirect** - OAuth happens in top window, then returns to iframe  
✅ **No `window.top` access** - All navigation handled properly by App Bridge  

## Verification

To test:

1. Open app in Shopify admin (embedded)
2. If store not connected, should redirect to OAuth (not login form)
3. After OAuth approval, should return to dashboard in iframe
4. Direct URL access (no shop/host params) should show login form

