# 📋 How to Add Webhooks in Your Shopify Store Admin

Since you can only add them in your dev store, here's how to do it:

## Steps:

1. **Go to your shop admin:**
   - Visit: `https://employee-suite.myshopify.com/admin`

2. **Navigate to Webhooks:**
   - Go to **Settings** (bottom left)
   - Click **Notifications**
   - Scroll down to **Webhooks** section

3. **Add the 3 compliance webhooks:**

   **Webhook 1: customers/data_request**
   - Click **Create webhook** (or **Add webhook**)
   - **Event:** Select "Customer data request"
   - **Format:** JSON
   - **URL:** `https://employeesuite-production.onrender.com/webhooks/customers/data_request`
   - Click **Save webhook**

   **Webhook 2: customers/redact**
   - Click **Create webhook** (or **Add webhook**)
   - **Event:** Select "Customer redaction"
   - **Format:** JSON
   - **URL:** `https://employeesuite-production.onrender.com/webhooks/customers/redact`
   - Click **Save webhook**

   **Webhook 3: shop/redact**
   - Click **Create webhook** (or **Add webhook**)
   - **Event:** Select "Shop redaction"
   - **Format:** JSON
   - **URL:** `https://employeesuite-production.onrender.com/webhooks/shop/redact`
   - Click **Save webhook**

---

## Exact URLs to Copy/Paste:

1. `https://employeesuite-production.onrender.com/webhooks/customers/data_request`
2. `https://employeesuite-production.onrender.com/webhooks/customers/redact`
3. `https://employeesuite-production.onrender.com/webhooks/shop/redact`

---

## After Adding:

1. Wait 2-3 minutes for Shopify to process
2. Go to **Shopify Partners Dashboard** → Your App → **Distribution**
3. Click **"Run"** to re-run automated checks
4. ✅ Webhook compliance should pass now!

---

## Verify They're Added:

After adding, you should see all 3 webhooks listed in:
- **Settings** → **Notifications** → **Webhooks**

They should show as active/webhook deliveries happening.
