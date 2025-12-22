# 🔧 FIX "Unauthorized Access" Error

## The Problem

You're getting "unauthorized access" when trying to install the app. This happens when:

1. **Redirect URI mismatch** - The redirect URI in the OAuth request doesn't match what's configured in Partners Dashboard
2. **App not in development mode** - The app needs to be in development/unlisted status
3. **Redirect URI not whitelisted** - The redirect URI must be added to the app's allowed redirect URLs

---

## ✅ FIX STEPS

### Step 1: Check Partners Dashboard Configuration

Go to **Shopify Partners Dashboard** → Your App → **App Setup**

**1. Check "Allowed redirection URLs":**
- Make sure this URL is listed: `https://employeesuite-production.onrender.com/auth/callback`
- If it's missing, click "Add URL" and add it

**2. Check App Status:**
- App should be in **Development** or **Unlisted** status (not Public/Published)
- If it's published, you can't install it in test stores the same way

**3. Verify Client ID:**
- The `client_id` in your OAuth URL should match the **API Key** shown in Partners Dashboard
- Your URL shows: `client_id=396cbab849f7c25996232ea4feda696a`
- Verify this matches your app's API key in Partners Dashboard

---

### Step 2: Verify Environment Variables

**In Render Dashboard**, check these environment variables are set:

- `SHOPIFY_API_KEY` - Should match the API Key in Partners Dashboard
- `SHOPIFY_API_SECRET` - Should match the Client Secret in Partners Dashboard  
- `SHOPIFY_REDIRECT_URI` - Should be `https://employeesuite-production.onrender.com/auth/callback`

**If `SHOPIFY_REDIRECT_URI` is missing or wrong**, the code will default to the correct URL, but it's better to set it explicitly.

---

### Step 3: Alternative Installation Method

If the direct URL method isn't working, try installing via Partners Dashboard:

1. Go to **Partners Dashboard** → **Stores**
2. Click on your test store (`testsuite-dev`)
3. Go to **Apps** tab
4. Find your app in the list
5. Click **Install** or **Test app**

This method handles the OAuth flow through Shopify's system.

---

### Step 4: Check App Configuration

**In Partners Dashboard → Your App → App Setup:**

1. **App URL:** Should be `https://employeesuite-production.onrender.com`
2. **Allowed redirection URLs:** Should include `https://employeesuite-production.onrender.com/auth/callback`
3. **Embedded app:** Should be enabled (if using embedded app)
4. **API version:** Should be `2024-10`

---

## 🎯 Most Common Fix

**99% of the time, this is because the redirect URI isn't in the "Allowed redirection URLs" list.**

**Quick fix:**
1. Partners Dashboard → Your App → App Setup
2. Scroll to "Allowed redirection URLs"
3. Add: `https://employeesuite-production.onrender.com/auth/callback`
4. Save
5. Try installing again

---

## ✅ After Fixing

Once you add the redirect URI and save:

1. Wait 1-2 minutes for changes to propagate
2. Try installing again using:
   ```
   https://employeesuite-production.onrender.com/install?shop=testsuite-dev.myshopify.com
   ```
3. Should work now! ✅
