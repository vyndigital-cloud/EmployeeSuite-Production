# 🔧 Fix "App Owned by a Shop" Error - Step by Step

## The Problem

You're getting this error:
```
It appears that this application is currently owned by a Shop. 
It must be migrated to the Shopify partners area before it can create charges with the API.
```

This happens when your app was created while logged into a **shop account** instead of a **Partners account**.

---

## ✅ SOLUTION: Step-by-Step

### Step 1: Check Current App Status

1. Go to: **https://partners.shopify.com**
2. Log in with your **Partners account** (not your shop account)
3. Click on **Apps** in the left sidebar
4. Find your app: **Employee Suite** (or similar name)

**If you see your app here** → Go to Step 2  
**If you DON'T see your app here** → Go to Step 3 (create new app)

---

### Step 2: Verify App Ownership

1. Click on your app name
2. Go to **App Setup** (left sidebar)
3. Scroll to **App information** section
4. Check:
   - Does it say "Public app" or "Custom app"?
   - Is there any mention of "Shop ownership" or "Migration needed"?

**If it's a Public app** → Your app is fine, skip to Step 4  
**If it says "Custom app" or mentions shop ownership** → You need a new app (Step 3)

---

### Step 3: Create New App in Partners Dashboard

**Option A: Create New App (RECOMMENDED)**

1. In Partners Dashboard, click **Apps** → **Create app**
2. Choose: **Create app manually** (not from template)
3. Fill in:
   - **App name:** `Employee Suite` (or your preferred name)
   - **App URL:** `https://employeesuite-production.onrender.com`
   - **Allowed redirection URL(s):** `https://employeesuite-production.onrender.com/auth/callback`
4. Click **Create app**

5. After creation, go to **API credentials** tab
6. Copy these values (you'll need them):
   - **Client ID** (API Key)
   - **Client Secret** (API Secret)

---

### Step 4: Update Environment Variables in Render

1. Go to: **https://dashboard.render.com**
2. Click on your **Web Service** (employeesuite-production)
3. Click **Environment** in left sidebar
4. Update these variables:

   ```
   SHOPIFY_API_KEY=<new-client-id-from-partners>
   SHOPIFY_API_SECRET=<new-client-secret-from-partners>
   ```

5. Click **Save Changes**

---

### Step 5: Verify Webhooks Configuration

1. In Partners Dashboard → Your App → **App Setup**
2. Scroll to **Webhooks** section
3. Verify these webhooks are configured:

   ```
   app/uninstall
   → https://employeesuite-production.onrender.com/webhooks/app/uninstall
   
   app_subscriptions/update
   → https://employeesuite-production.onrender.com/webhooks/app_subscriptions/update
   
   customers/data_request
   → https://employeesuite-production.onrender.com/webhooks/customers/data_request
   
   customers/redact
   → https://employeesuite-production.onrender.com/webhooks/customers/redact
   
   shop/redact
   → https://employeesuite-production.onrender.com/webhooks/shop/redact
   ```

4. If any are missing, add them and save

---

### Step 6: Verify Billing Settings

1. In Partners Dashboard → Your App → **App Setup**
2. Scroll to **Billing** section
3. Make sure:
   - ✅ **Billing is enabled**
   - ✅ **Pricing model:** "Manual pricing" (not "Managed pricing")

---

### Step 7: Redeploy/Restart App

1. In Render dashboard → Your Web Service
2. Click **Manual Deploy** → **Deploy latest commit**
   - OR just click **Restart** (environment variables update automatically)

---

### Step 8: Reinstall App in Test Store

1. Go to your Shopify admin: **https://admin.shopify.com/store/YOUR-STORE**
2. Go to **Settings** → **Apps and sales channels**
3. Find **Employee Suite** (old installation)
4. Click **...** → **Uninstall**
5. Click **Develop apps** → **Employee Suite** → **Install**
6. Complete OAuth flow
7. Try subscribing again

---

### Step 9: Test Billing

1. In your app, go to **Subscribe** page
2. Click **Subscribe Now**
3. Should redirect to Shopify payment approval (not show error)

---

## 🔍 Quick Diagnosis

### Check if API Key is from Partners:

Look at your current API key:
- Partners API keys start with: Various formats (not always obvious)
- Shop API keys: Usually shorter, different format

### Check Render Logs:

Look for this in logs:
```
BILLING DEBUG: Using API key: 8c81ac3c...
```

If you see errors after updating API key, the new credentials might not be active yet (wait 1-2 minutes).

---

## ⚠️ Common Issues

### Issue: "App not found in Partners Dashboard"
**Solution:** You need to create a new app. The old one was created in a shop account.

### Issue: "Still getting 422 error after updating API key"
**Solution:** 
1. Wait 2-3 minutes for environment variables to update
2. Restart the app in Render
3. Make sure you uninstalled and reinstalled the app in your shop

### Issue: "Can't find Client Secret in Partners Dashboard"
**Solution:**
1. Go to **Apps** → Your App → **API credentials** tab
2. Click **Reveal** next to Client Secret
3. Copy it (you won't see it again!)

---

## ✅ Success Checklist

- [ ] App exists in Partners Dashboard (not just shop admin)
- [ ] API credentials copied from Partners Dashboard
- [ ] Environment variables updated in Render
- [ ] Webhooks configured in Partners Dashboard
- [ ] Billing enabled in Partners Dashboard
- [ ] App restarted/redeployed in Render
- [ ] App reinstalled in test shop
- [ ] Billing subscription works without errors

---

## 📞 Still Having Issues?

If you're still getting the error after following all steps:

1. **Check Render logs** - Look for API key being used
2. **Verify Partners account** - Make sure you're logged into Partners, not shop admin
3. **Create fresh app** - Sometimes it's easier to start fresh
4. **Check Shopify status** - Make sure Partners dashboard is accessible

---

**Estimated Time:** 10-15 minutes  
**Difficulty:** Easy (just clicking around in dashboards)

