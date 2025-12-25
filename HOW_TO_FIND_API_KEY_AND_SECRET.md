# 🔑 How to Find Your Shopify API Key and Secret

## Your Current API Key (Already Found):

Based on your `shopify.app.toml` file, your API Key is:
```
396cbab849f7c25996232ea4feda696a
```

This should match what's in your Shopify Partners Dashboard.

---

## Where to Find Both Values:

### Step 1: Go to Shopify Partners Dashboard

1. Go to: **https://partners.shopify.com**
2. Log in with your Shopify Partners account
3. Click **Apps** in the left sidebar
4. Click on **"Employee Suite"** (your app)

### Step 2: Find API Credentials

Look for one of these sections (the exact name varies):

- **"App setup"** tab → Scroll down to **"API credentials"** section
- **"API credentials"** section
- **"Client credentials"** section  
- **"Credentials"** tab

### Step 3: Copy the Values

You should see:

1. **API key** (also called "Client ID"):
   ```
   396cbab849f7c25996232ea4feda696a
   ```
   - ✅ This should match what's in your `shopify.app.toml`
   - ✅ This is your `SHOPIFY_API_KEY`

2. **Client secret** (also called "API secret key" or "Secret"):
   ```
   shpss_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   - ⚠️ This is a long string starting with `shpss_` or similar
   - ⚠️ You may need to click **"Reveal"** or **"Show"** to see it
   - ✅ This is your `SHOPIFY_API_SECRET`

---

## Where to Set These in Render:

### Step 1: Go to Render Dashboard

1. Go to: **https://dashboard.render.com**
2. Click on your service (probably "employeesuite-production")
3. Click **Environment** in the left sidebar

### Step 2: Add/Verify Environment Variables

Click **"Add Environment Variable"** and add these:

#### Variable 1: SHOPIFY_API_KEY
- **Key:** `SHOPIFY_API_KEY`
- **Value:** `396cbab849f7c25996232ea4feda696a`
- ✅ This should already be set (verify it matches)

#### Variable 2: SHOPIFY_API_SECRET
- **Key:** `SHOPIFY_API_SECRET`
- **Value:** `shpss_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (the Client Secret from Partners Dashboard)
- ⚠️ **This is the one that's likely missing!**

---

## Quick Check:

After setting these in Render, your Environment Variables should have:

```
SHOPIFY_API_KEY=396cbab849f7c25996232ea4feda696a
SHOPIFY_API_SECRET=shpss_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## If You Can't Find the Client Secret:

If the Client Secret is not visible in Partners Dashboard:

1. Look for a **"Reveal"** or **"Show secret"** button
2. Click it to reveal the secret
3. Copy it immediately (it may hide again)
4. If there's no reveal button, look for **"Regenerate secret"** or **"Reset secret"**
5. Only regenerate if you're sure - it will invalidate the old secret

---

## After Setting in Render:

1. Render will automatically redeploy (or click "Manual Deploy")
2. Wait 2-3 minutes for deployment
3. Your OAuth should now work!

---

## Verify They're Set Correctly:

After deployment, check Render logs for:
- ✅ No errors about "SHOPIFY_API_KEY is not set"
- ✅ No errors about "SHOPIFY_API_SECRET is not set"
- ✅ OAuth routes should work without "Configuration Error"

---

**Need Help?** Tell me what you see in your Partners Dashboard and I'll guide you to the exact location!

