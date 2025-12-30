# Legacy Install Flow Configuration Guide

## Current Status: ✅ Use NEW Flow (Legacy = FALSE)

Your app is correctly configured to use the **NEW OAuth flow** (legacy install flow = **false**).

---

## How to Determine Which Flow to Use

### Use NEW Flow (Legacy = FALSE) ✅ **YOUR CURRENT SETTING**
**Use this if your app:**
- ✅ Uses Shopify App Bridge
- ✅ Supports embedded apps (runs in Shopify admin iframe)
- ✅ Handles `host` parameter for embedded installations
- ✅ Uses modern OAuth endpoints (`/admin/oauth/authorize`)

**Your app matches ALL of these criteria**, so **legacy install flow = false** is correct.

### Use Legacy Flow (Legacy = TRUE)
**Only use this if your app:**
- ❌ Does NOT use App Bridge
- ❌ Does NOT support embedded apps
- ❌ Uses old OAuth patterns
- ❌ Standalone apps only (no iframe embedding)

---

## Evidence Your App Uses NEW Flow

### 1. App Bridge Integration
Your code uses App Bridge for embedded apps:
- JavaScript includes App Bridge library
- Handles `host` parameter for embedded installations
- Uses session tokens for embedded authentication

### 2. OAuth Implementation
Your OAuth code (`shopify_oauth.py`):
- Uses standard OAuth endpoints: `https://{shop}/admin/oauth/authorize`
- Handles `host` parameter in state
- Supports embedded app redirects
- Uses `ACCESS_MODE = 'offline'` (standard, not legacy)

### 3. Embedded App Support
Your app:
- Detects embedded context via `host` parameter`
- Redirects to embedded URLs after OAuth
- Uses App Bridge for authentication in embedded mode

---

## Partners Dashboard Configuration

### Current Setting (Correct)
```
Legacy install flow: FALSE ✅
```

### What This Means
- Your app uses the modern OAuth flow
- Supports embedded apps via App Bridge
- Works with App Store installations
- Uses standard OAuth endpoints

---

## If You're Experiencing Issues

### Issue: OAuth Not Working
**Check:**
1. ✅ Redirect URI matches exactly: `https://employeesuite-production.onrender.com/auth/callback`
2. ✅ API Key and Secret are set correctly
3. ✅ Scopes match what's requested: `read_products,read_inventory,read_orders`
4. ✅ Legacy install flow = **FALSE** (your current setting)

### Issue: Embedded App Not Loading
**Check:**
1. ✅ App Bridge is initialized correctly
2. ✅ `host` parameter is being passed through OAuth flow
3. ✅ Post-OAuth redirect includes `host` parameter
4. ✅ App URL is whitelisted in Partners Dashboard

---

## When to Switch to Legacy Flow

**Only switch to legacy flow (true) if:**
- You're removing App Bridge support
- You're making a standalone-only app
- You're migrating from an old app that doesn't use App Bridge

**For your current app, keep legacy install flow = FALSE** ✅

---

## Verification

Your current OAuth flow:
1. User clicks install → `/install?shop={shop}&host={host}`
2. Redirects to Shopify OAuth: `https://{shop}/admin/oauth/authorize`
3. User authorizes → Shopify redirects to `/auth/callback`
4. App processes OAuth → Redirects to embedded URL with `host` parameter
5. App Bridge initializes → App loads in Shopify admin iframe

This is the **NEW flow** pattern, which requires **legacy install flow = FALSE**.

---

## Summary

✅ **Your current setting is CORRECT: Legacy install flow = FALSE**

Your app uses:
- App Bridge ✅
- Embedded apps ✅
- Modern OAuth flow ✅
- `host` parameter handling ✅

**Do NOT change to legacy flow (true)** unless you're removing App Bridge support.

<<<<<<< HEAD


=======
>>>>>>> 435f7f080afbe6538bc4e1b20a026900b2acdce6
