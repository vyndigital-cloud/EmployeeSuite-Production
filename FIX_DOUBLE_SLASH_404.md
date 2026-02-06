# 🔧 Fix: Double Slash 404 Error

## Problem
Getting 404 error at: `https://admin.shopify.com/store/employee-suite/apps//dashboard`

Notice the **double slash** (`//`) in the URL path.

## Root Cause
The Shopify Partners Dashboard "App URL" configuration has a trailing slash, which causes:
- Configured: `https://employeesuite-production.onrender.com/`
- Shopify appends: `/dashboard`
- Result: `//dashboard` (double slash = 404)

## Solution

### Step 1: Fix in Shopify Partners Dashboard

1. **Go to Shopify Partners Dashboard**
   - URL: https://partners.shopify.com
   - Navigate to: **Apps** → **Employee Suite**

2. **Open App Configuration**
   - Click on **Configuration** in the left sidebar
   - Go to **App Setup** section

3. **Check "App URL" Field**
   - Look for the **"App URL"** or **"Application URL"** field
   - Current (incorrect): `https://employeesuite-production.onrender.com/`
   - Correct: `https://employeesuite-production.onrender.com`
   
   **Remove the trailing slash!**

4. **Check "Default URL" or "Path" Field**
   - If there's a separate field for the default path
   - It might be set to `/` (empty path)
   - Options:
     - Leave it **empty** (recommended)
     - Set it to `dashboard` (without leading slash)
     - Set it to `/dashboard` (with leading slash)

5. **Save Changes**
   - Click **Save** at the bottom of the page
   - Wait for changes to propagate (usually instant)

### Step 2: Verify Configuration

After saving, your configuration should look like:

```
App URL: https://employeesuite-production.onrender.com
Redirect URLs: https://employeesuite-production.onrender.com/auth/callback
```

### Step 3: Test the Fix

1. **Clear browser cache** (important!)
   - Chrome: Cmd+Shift+Delete (Mac) or Ctrl+Shift+Delete (Windows)
   - Select "Cached images and files"
   - Click "Clear data"

2. **Try accessing your app again**
   - From Shopify admin: **Apps** → **Employee Suite**
   - The URL should now be: `https://admin.shopify.com/store/employee-suite/apps/dashboard`
   - (Single slash, not double)

3. **If still not working**, try:
   - Uninstall and reinstall the app
   - Use incognito/private browsing mode
   - Check the Network tab in browser DevTools

## Alternative: Check for Other Issues

If the Partners Dashboard looks correct, the issue might be elsewhere:

### Check 1: App Handle Configuration

In `shopify.app.toml`, verify:
```toml
handle = "employee-suite-7"
application_url = "https://employeesuite-production.onrender.com"
```

No trailing slash in `application_url`.

### Check 2: Embedded App Settings

In Shopify Partners Dashboard:
- **Distribution** → **Embedded app**
- Make sure "Embed your app in Shopify admin" is **enabled**
- Check that the frame ancestors are configured correctly

### Check 3: App Proxy (if configured)

If you have an app proxy configured:
- Go to **Configuration** → **App proxy**
- Make sure the subpath doesn't have issues
- Typically: `apps/employee-suite`

## Expected Behavior After Fix

✅ **Correct URL**: `https://admin.shopify.com/store/employee-suite/apps/dashboard`
✅ **App loads**: Dashboard appears embedded in Shopify admin
✅ **No 404 error**: Page loads successfully

## Troubleshooting

### Still getting 404?

1. **Check the actual URL in browser**
   - Copy the full URL from the address bar
   - Look for any unusual characters or double slashes

2. **Check Shopify Partners Dashboard logs**
   - Go to **Analytics** → **Errors**
   - Look for recent 404 errors

3. **Check your app's routing**
   - Make sure `/dashboard` route exists in your app
   - Check `core_routes.py` for the dashboard route

4. **Verify app is deployed**
   - Go to: https://employeesuite-production.onrender.com/dashboard
   - This should work directly (outside of Shopify)
   - If this 404s, the issue is in your app, not Shopify

### App loads but shows errors?

If the URL is correct but the app doesn't work:
- Check browser console for JavaScript errors
- Verify App Bridge is loading correctly
- Check that session tokens are being validated

## Quick Verification Commands

Check if your app responds directly:
```bash
curl -I https://employeesuite-production.onrender.com/dashboard
```

Should return `200 OK` or `302 Found` (redirect), not `404`.

## Need More Help?

If the issue persists:
1. Take a screenshot of the Shopify Partners Dashboard "App Setup" page
2. Copy the exact error message from the browser
3. Check browser console (F12) for JavaScript errors
4. Check Render logs for any errors

---

**Status**: Ready to fix - just need to update Shopify Partners Dashboard configuration
