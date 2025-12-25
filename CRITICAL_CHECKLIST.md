# 🔴 CRITICAL: OAuth Redirect Fix Checklist

## The Problem
Shopify redirects to: `admin.shopify.com/store/employee-suite/apps//auth/callback`  
Should redirect to: `https://employeesuite-production.onrender.com/auth/callback`

## ✅ Step-by-Step Checklist (Do ALL of these)

### 1. Check Render Logs
**Go to Render Dashboard → Your Service → Logs**

Look for this line when you try to install:
```
OAuth install: Using redirect_uri=...
```

**What it should show:**
```
OAuth install: Using redirect_uri=https://employeesuite-production.onrender.com/auth/callback
```

**If it shows something different, that's the problem.**

### 2. Check Partners Dashboard - App Setup
1. Go to: https://partners.shopify.com
2. Apps → **Employee Suite** → **App Setup** (left sidebar)
3. Scroll to: **"Allowed redirection URLs"** section
4. **EXACTLY what do you see?** (Write it down)
   - Should be: `https://employeesuite-production.onrender.com/auth/callback`
   - **NOT:** `/auth/callback` or `auth/callback` or anything else

### 3. Check Partners Dashboard - Active Version
1. Partners Dashboard → Apps → **Employee Suite** → **Versions** (left sidebar)
2. Which version has the green checkmark? (This is the Active version)
3. Click on that Active version
4. Check: **"Redirect URLs"** section
5. **What does it show?** (Write it down)
   - Should be: `https://employeesuite-production.onrender.com/auth/callback`

### 4. Verify App Is Actually Uninstalled
1. Go to: https://admin.shopify.com/store/employee-suite
2. Click: **Apps** (left sidebar)
3. **Is "Employee Suite" in the list?**
   - If YES → Click on it → Click **Uninstall** → Confirm
   - If NO → Good, it's already uninstalled

### 5. Check Browser Network Tab During OAuth
1. Open browser DevTools (F12)
2. Go to **Network** tab
3. Clear all requests
4. Try to install/authorize the app
5. Find request to: `employee-suite.myshopify.com/admin/oauth/authorize`
6. Click on it → **Query String Parameters** or **Payload**
7. Look for `redirect_uri` parameter
8. **What does it show?** (Copy the exact value)

It should be URL-encoded like:
```
redirect_uri=https%3A%2F%2Femployeesuite-production.onrender.com%2Fauth%2Fcallback
```

(That decodes to: `https://employeesuite-production.onrender.com/auth/callback`)

### 6. If Redirect URI Is Wrong In Network Tab

This means your code is sending the wrong URI. Check:

1. **Render Environment Variables:**
   - Go to Render Dashboard → Your Service → Environment
   - Check: `SHOPIFY_REDIRECT_URI`
   - **Is it set?** If yes, what value?
   - **Should be:** `https://employeesuite-production.onrender.com/auth/callback`
   - **Or:** Leave it unset (code will use default)

2. **If `SHOPIFY_REDIRECT_URI` is set incorrectly:**
   - Delete it or change it to: `https://employeesuite-production.onrender.com/auth/callback`
   - Redeploy the app

### 7. Complete Uninstall/Reinstall
After verifying everything above:

1. **Uninstall app from store** (Step 4)
2. **Wait 1 minute**
3. **Verify redirect URI in Partners Dashboard** (Steps 2 & 3)
4. **Reinstall via Partners Dashboard:**
   - Partners Dashboard → Stores → employee-suite → Apps tab
   - Click **Install** or **Test app**
5. **Test again**

## 📋 Report Back

After doing all steps, tell me:

1. What does Render log show for `redirect_uri`?
2. What redirect URI is shown in Partners Dashboard → App Setup?
3. What redirect URI is shown in the Active version?
4. What `redirect_uri` value appears in browser Network tab?
5. Did you uninstall the app completely?
6. Did you reinstall after checking everything?

## Most Likely Causes

1. **Redirect URI in Partners Dashboard is relative** (`/auth/callback` instead of full URL)
2. **Active version has different redirect URI** than App Setup
3. **App wasn't fully uninstalled** before reinstalling
4. **Environment variable `SHOPIFY_REDIRECT_URI` is set incorrectly** in Render

