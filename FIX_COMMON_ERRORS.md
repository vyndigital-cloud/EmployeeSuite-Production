# 🔧 FIX COMMON ERRORS - SIMPLE CHECKLIST

## ❌ Errors You're Seeing:
- ✗ Provides mandatory compliance webhooks → (Failed)
- ✗ Verifies webhooks with HMAC signatures → (Failed)

---

## ✅ SIMPLE FIX (Do These 3 Things):

### 1. **Verify Webhooks Are Registered in Partners Dashboard**

**Go to:** Shopify Partners → Your App → "App Setup" → "Webhooks"

**Check if these 3 webhooks exist:**
- `customers/data_request`
- `customers/redact`
- `shop/redact`

**If they DON'T exist:**
1. Click "Add webhook" for each one
2. Topic: `customers/data_request`
3. URL: `https://employeesuite-production.onrender.com/webhooks/customers/data_request`
4. Format: JSON
5. Repeat for other 2 webhooks

**Why:** Even though they're in `app.json`, Shopify might need them manually registered in the dashboard.

---

### 2. **Verify SHOPIFY_API_SECRET is Correct**

**In Render:**
- Go to Environment Variables
- Check `SHOPIFY_API_SECRET` exists
- Value should match: Partners Dashboard → API credentials → "Client secret"

**Double-check:** Make sure it's the "Client secret", not "API key"

---

### 3. **Wait for Deploy & Re-run Checks**

**After deploying the HMAC fix:**
1. Wait 2-3 minutes for Render to deploy
2. Go back to Partners Dashboard → Distribution
3. Click "Run" button to re-run checks
4. Should pass now

---

## 🧪 QUICK TEST (Verify Endpoints Work):

```bash
curl -X POST https://employeesuite-production.onrender.com/webhooks/customers/data_request
```

**Expected:** `{"error": "Invalid signature"}` with 401 status code
**Bad:** 404 Not Found = Endpoint doesn't exist

---

## 🎯 MOST LIKELY ISSUE:

**The webhooks might not be registered in Partners Dashboard.**

Even if they're in `app.json`, Shopify's automated checks might only look at what's registered in the Partners Dashboard webhooks section.

**Quick fix:** Just add them manually in Partners Dashboard → App Setup → Webhooks

---

## ✅ AFTER FIXING:

1. Webhooks registered in Partners Dashboard ✅
2. SHOPIFY_API_SECRET set correctly ✅
3. HMAC fix deployed (base64 encoding) ✅
4. Click "Run" in Partners Dashboard ✅
5. Should pass! 🎉

---

**TL;DR:**
1. Manually add the 3 webhooks in Partners Dashboard
2. Verify SHOPIFY_API_SECRET is correct
3. Re-run checks after deploy

That's it. These are literally the 3 things that fix the "common errors".
