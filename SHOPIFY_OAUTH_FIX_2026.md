# 🔧 Shopify OAuth "redirect_uri is not whitelisted" - Fix Guide

## The Problem
You're getting this error:
```
Oauth error invalid_request: The redirect_uri is not whitelisted
```

## Root Cause
The redirect URI your app is sending to Shopify **doesn't match** what's configured in your Shopify Partners Dashboard.

## Most Likely Cause: Environment Variable Override

Based on your previous fixes, the code is correct, but there's likely an **environment variable in Render** that's overriding it with the wrong value.

---

## 🚀 Quick Fix (Choose One Option)

### Option 1: Update Environment Variable in Render (Recommended)

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Select**: `employeesuite-production` service
3. **Click**: "Environment" tab (left sidebar)
4. **Find**: `SHOPIFY_REDIRECT_URI`
5. **Update the value to**:
   ```
   https://employeesuite-production.onrender.com/auth/callback
   ```
   ⚠️ **Important**: Remove any `/oauth` prefix if present!
6. **Click "Save Changes"** - This will trigger automatic redeploy

### Option 2: Delete Environment Variable (Simpler)

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Select**: `employeesuite-production` service
3. **Click**: "Environment" tab
4. **Find**: `SHOPIFY_REDIRECT_URI`
5. **Click the trash/delete icon** next to it
6. **Click "Save Changes"** - The code will use the correct default

---

## ✅ Verify Shopify Partners Dashboard Configuration

While waiting for Render to redeploy, verify your Shopify Partners Dashboard:

1. **Go to**: https://partners.shopify.com
2. **Navigate to**: Apps → Employee Suite → Configuration
3. **Check "App URL"**:
   ```
   https://employeesuite-production.onrender.com
   ```
   ⚠️ NO trailing slash!

4. **Check "Allowed redirection URL(s)"**:
   ```
   https://employeesuite-production.onrender.com/auth/callback
   ```
   ⚠️ Must match EXACTLY - no `/oauth` prefix!

5. **If it's wrong**, update it to:
   ```
   https://employeesuite-production.onrender.com/auth/callback
   ```

---

## 🧪 Test After Fix

Once Render redeploys (2-3 minutes):

### Test 1: Direct Install URL
```
https://employeesuite-production.onrender.com/oauth/install?shop=YOUR-STORE.myshopify.com
```
Replace `YOUR-STORE` with your actual Shopify store name.

### Test 2: From Shopify Admin
1. Go to your Shopify store admin
2. Navigate to: **Apps** → **App and sales channel settings**
3. Find your app and click **Install**
4. Should redirect to Shopify authorization page
5. After approving, should redirect back successfully

---

## 🔍 Debugging Steps

If still not working, check these:

### 1. Check Render Logs
1. Go to Render Dashboard → Logs
2. Look for this line when you try to connect:
   ```
   OAuth install: Using redirect_uri=...
   ```
3. The URI shown should be:
   ```
   https://employeesuite-production.onrender.com/auth/callback
   ```
4. If it shows `/oauth/auth/callback`, the environment variable is still wrong

### 2. Check Browser Network Tab
1. Open browser DevTools (F12)
2. Go to Network tab
3. Try connecting to Shopify
4. Look for the redirect to `admin/oauth/authorize`
5. Check the `redirect_uri` parameter in the URL
6. Should be: `redirect_uri=https%3A%2F%2Femployeesuite-production.onrender.com%2Fauth%2Fcallback`

### 3. Verify Environment Variables
Check these are set in Render:
- ✅ `SHOPIFY_API_KEY` - Your app's API key
- ✅ `SHOPIFY_API_SECRET` - Your app's API secret
- ❌ `SHOPIFY_REDIRECT_URI` - Should be deleted OR set to correct value

---

## 📋 Common Mistakes

### ❌ Wrong Redirect URIs:
```
https://employeesuite-production.onrender.com/oauth/auth/callback  ← Has /oauth prefix
https://employeesuite-production.onrender.com/callback             ← Missing /auth
https://employeesuite-production.onrender.com/auth/callback/       ← Trailing slash
```

### ✅ Correct Redirect URI:
```
https://employeesuite-production.onrender.com/auth/callback
```

---

## 🎯 Expected Outcome

After fixing:
1. ✅ No "redirect_uri is not whitelisted" error
2. ✅ Shopify OAuth authorization page loads
3. ✅ After clicking "Install", redirects back to your app
4. ✅ App shows "Store connected successfully!"

---

## 🆘 Still Having Issues?

If you've tried everything above and it's still not working:

1. **Check the exact error message** - Is it still "redirect_uri is not whitelisted"?
2. **Share the Render logs** - Look for the "OAuth install: Using redirect_uri=" line
3. **Verify Partners Dashboard** - Screenshot the "Allowed redirection URL(s)" field
4. **Check browser network tab** - What's the actual `redirect_uri` parameter being sent?

---

**Last Updated**: 2026-02-07  
**Status**: Awaiting environment variable fix in Render  
**Priority**: HIGH - App cannot connect to Shopify until fixed
