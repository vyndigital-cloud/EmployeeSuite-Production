# 🔧 App Store Installation Fix

## Issues Fixed

### 1. **Redirect URI Mismatch**
**Problem:** The code was trying to modify the redirect URI by adding query parameters (`?embedded=1`), but Shopify requires the redirect URI to match EXACTLY what's configured in Partners Dashboard.

**Fix:** Removed the redirect URI modification. The redirect URI now always matches what's in Partners Dashboard: `https://employeesuite-production.onrender.com/auth/callback`

### 2. **Missing Host Parameter Handling**
**Problem:** The code wasn't properly detecting and handling the `host` parameter that Shopify sends for embedded app installations (App Store).

**Fix:** 
- The `host` parameter is now properly extracted from the OAuth callback
- If `host` is provided during installation, it's encoded in the `state` parameter to preserve it through the OAuth flow
- After OAuth completes, if `host` is present, the app redirects to the embedded app URL format

### 3. **Incorrect Post-Installation Redirect**
**Problem:** After OAuth completed, embedded apps weren't being redirected to the proper embedded URL format.

**Fix:** When `host` parameter is present (App Store installation), the app now redirects to:
```
https://employeesuite-production.onrender.com/dashboard?shop={shop}&host={host}
```

This allows App Bridge to properly embed the app in the Shopify admin.

## What Changed

### `shopify_oauth.py`

1. **Install endpoint (`/install`):**
   - Removed redirect URI modification (no more `?embedded=1` query param)
   - Added `host` parameter preservation via `state` parameter
   - Proper URL encoding for state data

2. **Callback endpoint (`/auth/callback`):**
   - Added proper `host` parameter detection
   - Added state parameter parsing to recover `host` if needed
   - Added embedded app redirect logic
   - Proper logging for debugging

## Verification Steps

### 1. Verify Partners Dashboard Configuration

Go to **Shopify Partners Dashboard** → Your App → **App Setup**:

- ✅ **Allowed redirection URLs** must include:
  ```
  https://employeesuite-production.onrender.com/auth/callback
  ```
  (No query parameters, exact match)

- ✅ **App Status** should be **Development** or **Unlisted** (for testing)

### 2. Test App Store Installation

1. **Create a test store** in Partners Dashboard
2. **Install your app** from the App Store (or use the install URL)
3. **Verify the flow:**
   - OAuth authorization page appears
   - After clicking "Install", you're redirected back to your app
   - App loads embedded in Shopify admin
   - Store is connected and user is logged in

### 3. Check Logs

After installation, check your Render logs for:
```
Redirecting embedded app (App Store installation) to: https://employeesuite-production.onrender.com/dashboard?shop=...
```

This confirms the fix is working.

## Common Issues & Solutions

### Issue: "Redirect URI mismatch" error
**Solution:** Make sure the redirect URI in Partners Dashboard matches EXACTLY:
```
https://employeesuite-production.onrender.com/auth/callback
```
(No trailing slash, no query parameters)

### Issue: App installs but doesn't load embedded
**Solution:** 
- Check that `host` parameter is being passed
- Verify App Bridge is initialized in your dashboard HTML
- Check browser console for errors

### Issue: "HMAC verification failed"
**Solution:**
- Verify `SHOPIFY_API_SECRET` environment variable is set correctly
- Check that the secret matches what's in Partners Dashboard

## Next Steps

1. ✅ Deploy the updated code to production
2. ✅ Test installation in a development store
3. ✅ Verify embedded app loads correctly
4. ✅ Submit to App Store for review

## Technical Details

### How It Works Now

1. **User clicks "Install" in App Store**
   - Shopify redirects to `/install?shop={shop}&host={host}`
   - `host` is encoded in `state` parameter

2. **OAuth Flow**
   - User authorizes app
   - Shopify redirects to `/auth/callback?shop={shop}&code={code}&host={host}&state={state}`
   - `host` is extracted from query params or state

3. **Post-Installation**
   - If `host` is present → Redirect to embedded URL
   - If `host` is missing → Redirect to regular dashboard

This ensures App Store installations work correctly! 🎉

