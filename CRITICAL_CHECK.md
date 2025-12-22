# 🔴 CRITICAL: Check SHOPIFY_API_SECRET

If webhook checks are failing, this is the #1 most likely cause.

## Check Render Environment Variables:

1. Go to **Render Dashboard**
2. Click your service (the one running the app)
3. Go to **Environment** tab
4. Look for `SHOPIFY_API_SECRET`

**Is it set?**
- ✅ YES → Make sure it matches your Partners Dashboard Client Secret
- ❌ NO → **This is the problem!**

## How to Get the Correct Secret:

1. Go to **Shopify Partners Dashboard**
2. Click **Apps** → **Employee Suite**
3. Look for **API credentials** or **Client credentials** section
4. Copy the **"Client secret"** (NOT the API key, the SECRET)
5. Add it to Render as `SHOPIFY_API_SECRET`

## Why This Matters:

Without the correct `SHOPIFY_API_SECRET`, HMAC verification will always fail, causing automated checks to fail.

---

## After Adding/Verifying SHOPIFY_API_SECRET:

1. Render will automatically redeploy
2. Wait 2-3 minutes
3. Go to Partners Dashboard → Distribution → Run checks again
4. Should pass now!

**Check this first - it's the most common issue!**
