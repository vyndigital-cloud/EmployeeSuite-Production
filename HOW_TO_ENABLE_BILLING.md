# 🔧 How to Enable Billing in Shopify Partners Dashboard

## Step-by-Step Guide

### Step 1: Go to Partners Dashboard
1. Open: **https://partners.shopify.com**
2. Log in with your **Partners account**
3. Click **Apps** in the left sidebar

---

### Step 2: Select Your App
1. Find your app: **Employee Suite** (or whatever you named it)
2. Click on the app name

---

### Step 3: Navigate to App Setup
1. In the left sidebar, click **App Setup**
   - (This is where all app configuration is)

---

### Step 4: Find the Billing Section
1. Scroll down the App Setup page
2. Look for a section called **"Billing"** or **"App pricing"**
   - It's usually near the bottom of the page
   - Below webhooks, above GDPR settings

---

### Step 5: Enable Billing

**If you see a toggle/switch:**
- ✅ Turn it **ON** (Enable billing)

**If you see a dropdown:**
- Select **"Manual pricing"** or **"App pricing"**
- **NOT** "Managed pricing" (that's for Shopify-managed apps)

**If you see checkboxes:**
- ✅ Check **"Enable billing"** or **"Allow this app to charge merchants"**

**If you DON'T see a Billing section at all:**
- Your app might be set as a **Custom app** (can't use billing)
- You need to change it to a **Public app**:
  1. Look for **"App information"** or **"App type"** section
  2. Change from "Custom app" to **"Public app"**
  3. Save changes
  4. Billing section should now appear

---

### Step 6: Set Pricing Model

Make sure you select:
- ✅ **"Manual pricing"** - You control pricing via Billing API (what we're using)
- ❌ **NOT "Managed pricing"** - Shopify controls pricing (we don't want this)

---

### Step 7: Save Changes

1. Click **"Save"** button at the bottom of the page
2. Wait for confirmation message

---

### Step 8: Verify It's Enabled

You should see:
- ✅ **Billing status:** Enabled
- ✅ **Pricing model:** Manual pricing

---

## 📍 Exact Location in Partners Dashboard

```
Partners Dashboard
  └── Apps
      └── Your App Name
          └── App Setup (left sidebar)
              └── Scroll down to:
                  ├── App information
                  ├── App URL
                  ├── Allowed redirection URLs
                  ├── Webhooks
                  ├── Billing ← **HERE** (enable it)
                  └── GDPR settings
```

---

## ⚠️ Common Issues

### Issue: "Billing section doesn't exist"
**Cause:** App is set as "Custom app" instead of "Public app"  
**Solution:**
1. Look for **"App information"** section
2. Change app type to **"Public app"**
3. Save
4. Billing section should appear

### Issue: "Can't enable billing - grayed out"
**Cause:** App might not be fully configured  
**Solution:**
1. Make sure **App URL** is set
2. Make sure **Allowed redirection URLs** are configured
3. Try saving other sections first, then come back to billing

### Issue: "Only see 'Managed pricing' option"
**Cause:** This is for Shopify-managed apps (App Store listing)  
**Solution:**
- If you want to use the Billing API (like we do), you need **"Manual pricing"**
- If you only see "Managed pricing", you might need to:
  1. Check if your app is listed on the App Store
  2. Unlist it temporarily to enable manual pricing
  3. Or create a new app that's not listed yet

---

## ✅ What It Should Look Like

After enabling, you should see something like:

```
Billing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☑️ Enable billing
   Allow this app to charge merchants using the Billing API

Pricing model:
● Manual pricing
○ Managed pricing

[Save] button
```

---

## 🔍 Quick Check

**To verify billing is enabled:**
1. Go to App Setup
2. Find Billing section
3. Should see: **"Billing: Enabled"** or **"Manual pricing: Enabled"**

**If it says "Disabled" or you can't find it:**
- Follow the steps above to enable it

---

## 📞 Still Can't Find It?

If you absolutely cannot find the Billing section:

1. **Check app type:**
   - App information → App type → Should be "Public app"

2. **Check app status:**
   - Is the app in "Development" mode?
   - Some features only appear for certain app statuses

3. **Try different view:**
   - Sometimes sections are collapsed
   - Look for expand/collapse arrows
   - Or try scrolling more slowly

4. **Contact Shopify Partners Support:**
   - https://help.shopify.com/en/partners
   - They can help enable billing if there's an account issue

---

## 🎯 Next Steps After Enabling

1. ✅ Billing enabled in Partners Dashboard
2. ✅ Save changes
3. ✅ Update API credentials in Render (if you created new app)
4. ✅ Restart app in Render
5. ✅ Reinstall app in test store
6. ✅ Test subscription flow

---

**Estimated Time:** 2-3 minutes  
**Difficulty:** Easy (just clicking around)

