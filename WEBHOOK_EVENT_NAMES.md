# 📋 GDPR Compliance Webhook Event Names in Shopify

When adding webhooks in your store admin, look for these **exact event names** in the dropdown:

## The 3 Required Events:

1. **"Customer data request"**
   - URL: `https://employeesuite-production.onrender.com/webhooks/customers/data_request`

2. **"Customer redaction"**
   - URL: `https://employeesuite-production.onrender.com/webhooks/customers/redact`

3. **"Shop redaction"**
   - URL: `https://employeesuite-production.onrender.com/webhooks/shop/redact`

---

## If You Can't Find Them:

These compliance webhooks might:
- Be at the **bottom of the dropdown list**
- Be under a **"GDPR"** or **"Compliance"** section
- Require scrolling down in the dropdown

**Alternative names to look for:**
- "Customer data request" might also be: "Customer data_request" or "Data request"
- "Customer redaction" might also be: "Customer redact" or "Customer deletion request"
- "Shop redaction" might also be: "Shop redact" or "Shop deletion request"

---

## Quick Steps:

1. Scroll through the dropdown (it's long!)
2. Look for "Customer" section → find "Customer data request" and "Customer redaction"
3. Look for "Shop" section → find "Shop redaction"
4. For each one:
   - Select the event
   - Format: **JSON**
   - URL: Copy from above
   - Click **Save**

---

## If They're Still Not Visible:

Some compliance webhooks might only be configurable via:
- Shopify Partners Dashboard → App Setup → Webhooks
- Or via Admin API (programmatically)

Try scrolling to the very bottom of the dropdown first!
