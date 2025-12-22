# 🔑 How to Find Your Client Secret

Every Shopify app has a Client Secret. Here's where to find it:

## Method 1: Partners Dashboard

1. Go to: https://partners.shopify.com
2. Click **Apps** (left sidebar)
3. Click **Employee Suite** (your app)
4. Look for one of these sections:
   - **API credentials**
   - **Client credentials** 
   - **App credentials**
   - **Setup** tab → **API credentials**

5. You should see:
   - **API Key** (Client ID): `396cbab849f7c25996232ea4feda696a` (you have this)
   - **Client Secret**: Should be a long string starting with `shpss_` or similar

**If you don't see it:**
- Click **"Reveal"** or **"Show"** button
- It might be hidden by default for security

---

## Method 2: Check if It's Already in Render

1. Go to **Render Dashboard**
2. Click your service
3. Go to **Environment** tab
4. Look for `SHOPIFY_API_SECRET`

**If it exists:**
- ✅ Copy the value
- Use it to verify in Partners Dashboard

**If it doesn't exist:**
- ❌ This is the problem!
- You need to add it from Partners Dashboard

---

## If You Really Can't Find It:

You might need to **regenerate** the Client Secret:

1. Partners Dashboard → Your App
2. Look for **API credentials** or **Client credentials**
3. There should be a **"Regenerate"** or **"Reset secret"** button
4. Click it to generate a new secret
5. **Copy it immediately** (you can only see it once)
6. Add it to Render as `SHOPIFY_API_SECRET`

---

## Quick Check:

In Partners Dashboard, what sections/tabs do you see when you click on "Employee Suite"?

List them and I'll tell you which one has the secret!
