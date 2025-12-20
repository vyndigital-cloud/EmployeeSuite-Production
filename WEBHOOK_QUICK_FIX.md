# ⚡ WEBHOOK QUICK FIX - 5 MINUTE CHECK

## 🎯 MOST LIKELY ISSUE: Missing SHOPIFY_API_SECRET

**90% of the time, this is the problem.**

---

## ✅ QUICK CHECK (2 minutes)

### 1. Check if SHOPIFY_API_SECRET exists in Render:
- Go to Render Dashboard
- Your Service → Environment
- Look for `SHOPIFY_API_SECRET`
- **If missing:** That's your problem!

### 2. How to Get It:
1. Go to: https://partners.shopify.com
2. Click your "Employee Suite" app
3. Click "API credentials" (in left sidebar or Overview)
4. Copy the "Client secret" value
5. Add to Render: `SHOPIFY_API_SECRET=paste_here`
6. Redeploy

---

## 🔍 VERIFY WEBHOOKS ARE REGISTERED

### In Shopify Partners Dashboard:
1. Your App → "App Setup" → "Webhooks"
2. Check these 3 exist:
   - ✅ `customers/data_request`
   - ✅ `customers/redact`  
   - ✅ `shop/redact`

**If they don't exist:**
- Click "Add webhook"
- Add each one manually
- URL format: `https://employeesuite-production.onrender.com/webhooks/[endpoint]`

---

## 🧪 QUICK TEST

**Test if endpoints exist:**
```bash
curl -X POST https://employeesuite-production.onrender.com/webhooks/customers/data_request
```

**Expected Response:**
- ✅ `{"error": "Invalid signature"}` with 401 = Endpoint exists, just needs HMAC
- ❌ `404 Not Found` = Endpoint doesn't exist (deployment issue)
- ❌ `500 Internal Server Error` = Code error (check logs)

---

## 🚨 IF STILL FAILING AFTER SETTING SHOPIFY_API_SECRET

1. **Wait 2-3 minutes** after adding environment variable
2. **Redeploy** the app in Render (even if it says it auto-deployed)
3. **Click "Run"** again in Shopify Partners Dashboard
4. **Check Render logs** for webhook requests

---

## ✅ SUCCESS LOOKS LIKE:

In Shopify Partners Dashboard:
- ✅ Provides mandatory compliance webhooks → Green checkmark
- ✅ Verifies webhooks with HMAC signatures → Green checkmark

In Render Logs:
- Webhook requests from Shopify
- "Invalid webhook signature" messages (before you add SHOPIFY_API_SECRET)
- No errors after adding SHOPIFY_API_SECRET

---

**TL;DR: Add `SHOPIFY_API_SECRET` to Render environment variables. That's usually it!**
