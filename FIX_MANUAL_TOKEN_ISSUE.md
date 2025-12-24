# 🔧 Fix Manual Token Issue - Complete OAuth Re-connection

## The Problem

Your database has a **manual access token** (`shpat_5776...`) that was created via Shopify Admin → Settings → Apps → Custom App. These tokens are **"Shop-owned"** and **cannot create charges** via the Billing API.

**Only OAuth tokens** from Partner-managed apps can create recurring_application_charges.

## The Root Cause

Even though your API key is correct (`8c81ac3c...`), the old token was created manually and is linked to a Custom App, not your Partners app.

## Solution: Force OAuth Re-authorization

### Step 1: Clear the Old Token (Already Done by Code)

The code already detects this error and clears the token automatically. When you try to create a charge and get the 422 error, the code will:
1. Clear the old `access_token`
2. Set `is_active = False`
3. Redirect you to OAuth install flow

### Step 2: Complete OAuth Flow

When you're redirected to `/install?shop=testsuite-dev.myshopify.com`, you need to:

1. **Click "Install"** on the Shopify authorization page
2. **Grant permissions** (you'll see a permissions screen)
3. **Complete the OAuth callback** - your app will receive a new authorization code
4. **Exchange for Partner token** - the code automatically exchanges this for a new `shpat_` token that's linked to your Partners app

### Step 3: Verify in Partners Dashboard

Make sure your app is configured correctly:

1. Go to: **https://partners.shopify.com**
2. Click: **Apps** → Your app
3. Click: **App Setup** → **Distribution**
4. Ensure: **Distribution** is set to **"Public"** (even if unlisted)
5. Ensure: **API key** matches what's in Render (`8c81ac3c...`)

### Step 4: Test Billing

After OAuth completes:

1. Go to `/subscribe`
2. Click "Subscribe" or "Create Charge"
3. The new OAuth token should work with the Billing API

## What Changed in Code

✅ **OAuth callback now uses logged-in user**: When you're already logged in (e.g., from `/settings/shopify`), the OAuth callback will update YOUR store record, not create a new shop-based user.

✅ **Auto-redirect to OAuth**: When billing detects an old token, it automatically redirects to `/install` instead of showing an error.

✅ **Better logging**: You'll see in logs which API key is being used and which user the store is linked to.

## Next Steps

1. **Disconnect the current store** (if it still has the old token):
   - Go to `/settings/shopify`
   - Click "Disconnect Store"

2. **Reconnect via OAuth**:
   - Click "Quick Connect" → Enter shop domain → "Connect with Shopify"
   - This will trigger the OAuth flow
   - Grant permissions
   - Complete installation

3. **Test billing**:
   - Go to `/subscribe`
   - Create a charge
   - Should work with the new OAuth token

## Why This Works

- **Manual tokens** = Created in Shopify Admin → Shop-owned → ❌ No billing API access
- **OAuth tokens** = Created via Partners app → Partner-owned → ✅ Full billing API access

The OAuth flow uses your Partners API key (`8c81ac3c...`) to create a token that's cryptographically linked to your Partner identity, which unlocks the Billing API.

