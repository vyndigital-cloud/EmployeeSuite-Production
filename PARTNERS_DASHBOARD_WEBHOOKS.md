# ✅ HOW TO ADD COMPLIANCE WEBHOOKS (Correct Way)

## ❌ Why Store Admin Doesn't Work

The 3 GDPR compliance webhooks (`customers/data_request`, `customers/redact`, `shop/redact`) are **NOT available** in the regular store admin webhook dropdown.

They can **ONLY** be added via:
- ✅ Shopify Partners Dashboard
- ✅ Admin API (programmatic)
- ✅ shopify.app.toml (CLI)

---

## ✅ CORRECT WAY: Partners Dashboard

### Step-by-Step:

1. **Go to Shopify Partners Dashboard:**
   - Visit: https://partners.shopify.com
   - Log in

2. **Navigate to Your App:**
   - Click **Apps** (left sidebar)
   - Click **Employee Suite**

3. **Go to App Setup:**
   - Click **App Setup** (left sidebar)
   - Scroll down to **"Webhooks"** section

4. **Add the 3 webhooks:**
   - Click **"Add webhook"** or **"Create webhook"**
   - For each one:
   
   **Webhook 1:**
   - **Topic/Event:** `customers/data_request` (type it exactly)
   - **URL:** `https://employeesuite-production.onrender.com/webhooks/customers/data_request`
   - **Format:** JSON
   - Click **Save**
   
   **Webhook 2:**
   - **Topic/Event:** `customers/redact` (type it exactly)
   - **URL:** `https://employeesuite-production.onrender.com/webhooks/customers/redact`
   - **Format:** JSON
   - Click **Save**
   
   **Webhook 3:**
   - **Topic/Event:** `shop/redact` (type it exactly)
   - **URL:** `https://employeesuite-production.onrender.com/webhooks/shop/redact`
   - **Format:** JSON
   - Click **Save**

---

## 📋 Exact URLs (Copy/Paste):

1. `https://employeesuite-production.onrender.com/webhooks/customers/data_request`
2. `https://employeesuite-production.onrender.com/webhooks/customers/redact`
3. `https://employeesuite-production.onrender.com/webhooks/shop/redact`

---

## ✅ After Adding:

1. Wait 2-3 minutes
2. Go to **Partners Dashboard** → Your App → **Distribution**
3. Click **"Run"** to re-run automated checks
4. ✅ Compliance checks should pass!

---

## 🎯 This is the ONLY way to add compliance webhooks!

They cannot be added from store admin - they must be added in Partners Dashboard.
