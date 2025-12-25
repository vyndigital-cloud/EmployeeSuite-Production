# How to Verify and Fix OAuth Redirect URI

## The Problem
OAuth callback is going to:
```
admin.shopify.com/store/employee-suite/apps//auth/callback
```
Instead of:
```
https://employeesuite-production.onrender.com/auth/callback
```

## Why This Happens
Shopify uses the redirect URI configured in **Partners Dashboard**, NOT what's in your code. Even if your code is correct, Shopify will use what's configured in the dashboard.

## Step-by-Step Fix

### 1. Check Partners Dashboard

1. Go to: https://partners.shopify.com
2. Click: **Apps** (left sidebar)
3. Click: **Employee Suite** (your app)
4. Click: **App Setup** (left sidebar)
5. Scroll to: **Allowed redirection URL(s)** section

### 2. What You Should See

**CORRECT configuration:**
```
https://employeesuite-production.onrender.com/auth/callback
```

**WRONG configurations (that cause the error):**
- ❌ `/auth/callback`
- ❌ `auth/callback`  
- ❌ `https://admin.shopify.com/auth/callback`
- ❌ `employeesuite-production.onrender.com/auth/callback` (missing https://)

### 3. If It's Wrong, Fix It

1. Click the **Edit** button (or pencil icon) next to the redirect URI
2. Enter: `https://employeesuite-production.onrender.com/auth/callback`
3. **VERIFY:**
   - ✅ Starts with `https://`
   - ✅ Full domain: `employeesuite-production.onrender.com`
   - ✅ Path: `/auth/callback`
   - ✅ No trailing slash
   - ✅ Matches exactly what's in `app.json` line 9
4. Click **Save**

### 4. Critical: Reinstall the App

After changing the redirect URI:
1. The app MUST be **uninstalled and reinstalled** from your Shopify store
2. Old installations still use the old redirect URI
3. New installations will use the new one

### 5. Verify the Fix

After reinstalling, the OAuth flow should redirect to:
```
https://employeesuite-production.onrender.com/auth/callback?code=...
```

NOT:
```
admin.shopify.com/store/.../apps//auth/callback
```

## Code Verification

Your code is already correct:
- ✅ `shopify_oauth.py` line 24: `REDIRECT_URI = 'https://employeesuite-production.onrender.com/auth/callback'`
- ✅ `app.json` line 9: `"https://employeesuite-production.onrender.com/auth/callback"`
- ✅ `shopify.app.toml` line 16: `"https://employeesuite-production.onrender.com/auth/callback"`

**The problem is 100% in Partners Dashboard configuration.**

## If It Still Doesn't Work

1. Double-check there are no typos
2. Make sure there's no trailing space
3. Ensure it matches exactly: `https://employeesuite-production.onrender.com/auth/callback`
4. Wait 2-3 minutes after saving
5. Uninstall and reinstall the app completely

