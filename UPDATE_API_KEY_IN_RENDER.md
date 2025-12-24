# 🔑 Update Shopify API Key in Render - DO THIS NOW

## The Problem
Your app is using the **OLD API key** from the environment variable. The code is correct - it reads from `SHOPIFY_API_KEY`, but Render still has the old value set.

## Fix: Update Environment Variable in Render

### Step 1: Get Your NEW API Key from Partners Dashboard

1. Go to: **https://partners.shopify.com**
2. Click: **Apps** → Your app
3. Click: **App Setup** (left sidebar)
4. Scroll to: **Client credentials**
5. Copy the **API key** (starts with something like `396cbab8...` or similar)

### Step 2: Update in Render Dashboard

1. Go to: **https://dashboard.render.com**
2. Click on your service: **employeesuite-production**
3. Click: **Environment** (left sidebar)
4. Find: **`SHOPIFY_API_KEY`** in the list
5. Click: **Edit** (pencil icon) or click the value
6. **Replace** the old API key with the NEW one from Partners Dashboard
7. Click: **Save Changes**

### Step 3: Restart Service

After updating the environment variable:
1. Still in Render dashboard → Your service
2. Click: **Manual Deploy** (top right)
3. Select: **Deploy latest commit**
4. Wait 2-5 minutes for restart

**OR** just click **"Restart"** button if available.

### Step 4: Verify

1. Go to Render dashboard → Your service → **Logs**
2. Look for OAuth callback logs
3. You should see: `OAUTH DEBUG: Using API key for token exchange: [NEW_KEY_FIRST_8_CHARS]...`
4. The first 8 characters should match your NEW API key from Partners Dashboard

---

## Quick Checklist

- [ ] Get new API key from Partners Dashboard → App Setup → Client credentials
- [ ] Go to Render → Your service → Environment
- [ ] Update `SHOPIFY_API_KEY` with NEW value
- [ ] Save changes
- [ ] Restart service (Manual Deploy or Restart button)
- [ ] Check logs to verify new API key is being used

---

## Why This Matters

- ❌ **Old API key:** OAuth won't work, billing won't work, embedded app won't work
- ✅ **New API key:** Everything works, app connects properly to Shopify

The code already reads from `SHOPIFY_API_KEY` environment variable - you just need to update it in Render's dashboard!

