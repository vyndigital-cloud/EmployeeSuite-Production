# 🚨 CRITICAL: Deploy shopify.app.toml

**The `shopify.app.toml` file MUST be deployed using Shopify CLI for compliance webhooks to register.**

---

## ⚠️ THE ISSUE

Shopify's automated checks are failing because:
- Compliance webhooks **MUST** be in `shopify.app.toml` (not `app.json`)
- The file **MUST** be deployed using `shopify app deploy` command
- Just pushing to GitHub/deploying to Render is NOT enough

---

## ✅ SOLUTION

### Option 1: Deploy with Shopify CLI (RECOMMENDED)

1. **Install Shopify CLI** (if not already installed):
   ```bash
   npm install -g @shopify/cli @shopify/theme
   ```

2. **Link your app**:
   ```bash
   cd /Users/essentials/Documents/1EmployeeSuite-FIXED
   shopify app generate extension
   # OR if already linked:
   shopify app info
   ```

3. **Deploy the configuration**:
   ```bash
   shopify app deploy
   ```

This will deploy your `shopify.app.toml` configuration to Shopify, registering the compliance webhooks.

---

### Option 2: Upload app.json via Partners Dashboard (IF CLI not available)

If you can't use Shopify CLI:

1. Go to **Shopify Partners Dashboard** → Your App → **Distribution**
2. Look for **"App configuration"** or **"Upload app.json"** option
3. Upload your `app.json` file (may need to keep compliance webhooks there too)
4. Shopify will sync the configuration

---

### Option 3: Register Webhooks Manually (TEMPORARY WORKAROUND)

**This is NOT recommended long-term, but might work for testing:**

1. Go to **Shopify Partners Dashboard** → Your App
2. Find the webhook configuration section
3. Manually add the 3 compliance webhooks:
   - Topic: `customers/data_request` → URL: `https://employeesuite-production.onrender.com/webhooks/customers/data_request`
   - Topic: `customers/redact` → URL: `https://employeesuite-production.onrender.com/webhooks/customers/redact`
   - Topic: `shop/redact` → URL: `https://employeesuite-production.onrender.com/webhooks/shop/redact`

---

## 🔍 VERIFY IT WORKED

After deploying:

1. Wait 2-3 minutes
2. Go to **Partners Dashboard** → **Distribution**
3. Click **"Run"** to re-run automated checks
4. Check if the webhook errors are gone

---

## 📝 NOTES

- The `shopify.app.toml` file is now in your repo ✅
- Your endpoints are correctly implemented ✅
- HMAC verification is working ✅
- **You just need to deploy the TOML file to Shopify** ⚠️

Without deploying via Shopify CLI, Shopify's system won't know about your compliance webhook configuration!
