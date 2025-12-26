# What's Going On - OAuth Redirect Issue

## The Problem

OAuth callback is redirecting to:
```
admin.shopify.com/store/employee-suite/apps//auth/callback
```

Instead of:
```
https://employeesuite-production.onrender.com/auth/callback
```

## Why This Is Happening

Shopify uses the **redirect URI configured in Partners Dashboard**, NOT what your code sends. Even if your code sends the correct URI, Shopify validates it against the Partners Dashboard setting.

## Quick Diagnosis

The double slash `//auth/callback` suggests the redirect URI in Partners Dashboard is set to a **relative path** like:
- ❌ `/auth/callback`
- ❌ `auth/callback`

Instead of the **full absolute URL**:
- ✅ `https://employeesuite-production.onrender.com/auth/callback`

## The Fix (100% Required)

**This is NOT a code issue - it's a Partners Dashboard configuration issue.**

### Step 1: Check Partners Dashboard

1. Go to: https://partners.shopify.com
2. Apps → **Employee Suite** → **App Setup**
3. Scroll to: **Allowed redirection URL(s)**
4. Look at what's currently set

### Step 2: Fix It

Change it to exactly (copy-paste this):
```
https://employeesuite-production.onrender.com/auth/callback
```

### Step 3: Critical - Reinstall

After fixing:
1. **Uninstall** the app from your Shopify store
2. **Reinstall** the app
3. Old installations keep the old redirect URI - you MUST reinstall

## Why Code Can't Fix This

Your code is correct:
```python
REDIRECT_URI = 'https://employeesuite-production.onrender.com/auth/callback'
```

But Shopify **validates** the redirect_uri parameter against what's configured in Partners Dashboard. If they don't match exactly, Shopify either:
- Rejects the OAuth request, OR
- Uses a default/incorrect redirect URI (which is what's happening)

## Verification Checklist

- [ ] Partners Dashboard shows: `https://employeesuite-production.onrender.com/auth/callback`
- [ ] No trailing slash
- [ ] Starts with `https://`
- [ ] Full domain (not relative path)
- [ ] Saved in Partners Dashboard
- [ ] App uninstalled and reinstalled after fixing

## If Still Not Working

1. Double-check there are no spaces or typos
2. Make sure it's saved in Partners Dashboard
3. Wait 3-5 minutes after saving
4. Try a different browser/incognito mode
5. Clear browser cache

**Bottom line: This MUST be fixed in Partners Dashboard - code changes won't help.**


