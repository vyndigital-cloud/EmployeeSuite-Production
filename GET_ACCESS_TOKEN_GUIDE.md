# 🔑 How to Get Access Token for Webhook Registration

Since the automatic webhook registration didn't work, we need to manually register them. Here's how to get the access token:

## Option 1: Create Custom App (RECOMMENDED)

1. **Go to your shop admin:**
   - Visit: `https://employee-suite.myshopify.com/admin`

2. **Navigate to Apps:**
   - Go to **Settings** → **Apps and sales channels**
   - Click **Develop apps** (bottom of page)

3. **Create a new app:**
   - Click **Create an app**
   - Name it: "Webhook Registration" (or any name)
   - Click **Create app**

4. **Configure Admin API scopes:**
   - Click **Configure Admin API scopes**
   - Find and enable:
     - `read_webhooks`
     - `write_webhooks`
   - Click **Save**

5. **Install the app:**
   - Click **Install app**
   - Confirm installation

6. **Get the Admin API access token:**
   - Click **API credentials** tab
   - Under **Admin API access token**, click **Reveal token once**
   - **Copy the token** (starts with `shpat_` or `shpss_`)

7. **Register webhooks:**
   ```bash
   python3 find_shop_and_register.py [YOUR_NEW_TOKEN] employee-suite.myshopify.com
   ```

---

## Option 2: Use Existing App Token (if app is installed)

If your Employee Suite app is already installed, the access token should be in the production database. Since we can't access it directly, you can:

1. **Check Render Logs:**
   - Go to Render Dashboard → Your Service → Logs
   - Look for OAuth callback logs
   - The access token might be logged (be careful, it's sensitive!)

2. **Re-install the app:**
   - Uninstall the app from the shop
   - Re-install it via OAuth
   - The webhooks should register automatically this time

---

## Option 3: Quick Manual Registration (Easiest)

If you just want to register webhooks quickly without tokens:

1. Go to **Shopify Partners Dashboard** → Your App → **App Setup** → **Webhooks**
2. Manually add these 3 webhooks:
   - Topic: `customers/data_request`
     URL: `https://employeesuite-production.onrender.com/webhooks/customers/data_request`
   - Topic: `customers/redact`
     URL: `https://employeesuite-production.onrender.com/webhooks/customers/redact`
   - Topic: `shop/redact`
     URL: `https://employeesuite-production.onrender.com/webhooks/shop/redact`

**This is the fastest way!** ✅

---

## Which Option to Choose?

- **Fastest:** Option 3 (manual in Partners Dashboard)
- **Most reliable:** Option 1 (custom app for Admin API)
- **If re-installation works:** Option 2

**I recommend Option 3** - just add them manually in Partners Dashboard. It's the quickest and they'll be registered properly!
