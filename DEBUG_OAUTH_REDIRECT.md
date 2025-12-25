# Debug OAuth Redirect Issue

## Current Problem

OAuth callback is going to:
```
admin.shopify.com/store/employee-suite/apps//auth/callback
```

Even though redirect URI is correctly configured as:
```
https://employeesuite-production.onrender.com/auth/callback
```

## Debugging Steps

### 1. Check What Redirect URI Code Is Actually Sending

Add temporary logging to see what's being sent:

In `shopify_oauth.py` around line 189, you should see:
```python
logger.info(f"OAuth install: Using redirect_uri={REDIRECT_URI} (must match Partners Dashboard exactly)")
```

**Check your Render logs** to see what redirect URI is actually being sent in the OAuth request.

### 2. Verify Both Configuration Locations

In Partners Dashboard, check redirect URI in **TWO places**:

**Location 1: App Setup**
- Partners Dashboard → Apps → Employee Suite → **App Setup** (left sidebar)
- Find: **"Allowed redirection URLs"**
- Should have: `https://employeesuite-production.onrender.com/auth/callback`

**Location 2: App Version (if applicable)**
- Partners Dashboard → Apps → Employee Suite → **Versions** (left sidebar)
- Click on the **Active** version
- Check: **"Redirect URLs"** section
- Should have: `https://employeesuite-production.onrender.com/auth/callback`

### 3. Check for Multiple Redirect URIs

Make sure there's **only ONE** redirect URI listed, and it's exactly:
```
https://employeesuite-production.onrender.com/auth/callback
```

**Common mistakes:**
- Having both `/auth/callback` AND the full URL
- Having a typo or trailing slash
- Having multiple versions with different redirect URIs

### 4. Verify Active App Version

1. Go to Partners Dashboard → Apps → Employee Suite → **Versions**
2. Note which version has the green checkmark (Active)
3. Click on that version
4. Verify the redirect URI is correct on that specific version

### 5. Complete Uninstall/Reinstall Process

**This is CRITICAL - must be done completely:**

1. **In Shopify Store Admin:**
   - Apps → Find "Employee Suite"
   - Click **Uninstall**
   - Wait for confirmation

2. **In Partners Dashboard:**
   - Apps → Employee Suite → **App Setup**
   - Verify redirect URI is correct
   - **Save** (even if it's already correct, click Save to ensure)

3. **Wait 2-3 minutes** for changes to propagate

4. **Reinstall:**
   - Partners Dashboard → Stores → Your Store → Apps tab
   - OR go directly to: `https://employeesuite-production.onrender.com/install?shop=employee-suite.myshopify.com`

### 6. Check Browser Network Tab

During OAuth flow:
1. Open browser DevTools (F12)
2. Go to **Network** tab
3. Try to install/authorize app
4. Find the request to: `https://employee-suite.myshopify.com/admin/oauth/authorize`
5. Look at the **Query String Parameters**
6. Check what `redirect_uri` value is being sent

It should show:
```
redirect_uri=https%3A%2F%2Femployeesuite-production.onrender.com%2Fauth%2Fcallback
```

(That's URL-encoded version of `https://employeesuite-production.onrender.com/auth/callback`)

### 7. Try Creating a New App Version

Sometimes old versions have cached settings:

1. Partners Dashboard → Apps → Employee Suite → **Versions**
2. Click **Create a version**
3. Set redirect URI: `https://employeesuite-production.onrender.com/auth/callback`
4. **Activate** this new version
5. Uninstall and reinstall app

## Most Likely Cause

Given that the redirect URI appears correct in Partners Dashboard, the most likely issues are:

1. **App not fully uninstalled/reinstalled** - Old installation still using cached redirect URI
2. **Wrong app version active** - A different version has incorrect redirect URI
3. **Multiple redirect URIs configured** - Shopify might be using the wrong one
4. **App Setup vs Version mismatch** - Redirect URI in one place but not the other

## Next Steps

1. Check Render logs to see what redirect URI code is sending
2. Verify redirect URI in BOTH App Setup AND the active version
3. Do a complete uninstall/reinstall
4. Check browser network tab during OAuth to see actual redirect_uri parameter

