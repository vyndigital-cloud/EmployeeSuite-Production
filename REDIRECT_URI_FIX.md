# Fix: OAuth Redirect URI 404 Error

## Problem
Getting 404 error at:
```
https://admin.shopify.com/store/employee-suite/apps//auth/callback?code=...
```

## Root Cause
The redirect URI in **Shopify Partners Dashboard** is incorrectly configured. It's likely set to a relative path (`/auth/callback`) instead of the full absolute URL.

## Fix Required in Partners Dashboard

1. Go to: https://partners.shopify.com
2. Navigate to: Your App → **App Setup**
3. Find section: **Allowed redirection URL(s)**
4. **MUST be set to** (exact URL, no trailing slash):
   ```
   https://employeesuite-production.onrender.com/auth/callback
   ```

   **NOT:**
   - ❌ `/auth/callback`
   - ❌ `auth/callback`
   - ❌ `https://admin.shopify.com/auth/callback`
   - ❌ Any other domain

## Verification

After updating:
1. Click **Save** in Partners Dashboard
2. Wait 1-2 minutes for changes to propagate
3. The redirect URI in your code is already correct:
   ```python
   REDIRECT_URI = 'https://employeesuite-production.onrender.com/auth/callback'
   ```
4. Try installing the app again

## Why This Happens

Shopify uses the redirect URI exactly as configured in Partners Dashboard. If you set a relative path, Shopify may try to construct the URL relative to the Shopify admin domain, resulting in incorrect URLs like `admin.shopify.com/apps//auth/callback`.

## Current Configuration

- ✅ Code: `https://employeesuite-production.onrender.com/auth/callback`
- ❌ Partners Dashboard: Likely set incorrectly (check and update)

