# ✅ VERIFY YOUR DEPLOYMENT WORKED

Since you already deployed, let's verify everything is working:

---

## 🧪 Quick Test (30 seconds)

**Test if webhooks respond correctly:**

```bash
curl -X POST https://employeesuite-production.onrender.com/webhooks/customers/data_request \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Hmac-Sha256: test" \
  -d '{"test": "data"}'
```

**Expected Response:**
```json
{"error": "Invalid signature"}
```
**Status Code:** `401` ✅

**If you get 404:** Endpoints not deployed yet  
**If you get 500:** Check Render logs for errors

---

## ✅ Check Partners Dashboard

1. Go to **Shopify Partners Dashboard** → Your App → **Distribution**
2. Click **"Run"** button to re-run automated checks
3. Wait 1-2 minutes for results

**What you should see:**
- ✅ Provides mandatory compliance webhooks (Pass)
- ✅ Verifies webhooks with HMAC signatures (Pass)

---

## 📋 What Should Be Working

### Code (Already Done ✅):
- ✅ All 3 webhook endpoints implemented
- ✅ HMAC verification working (base64 encoded)
- ✅ Returns 401 for invalid signatures
- ✅ Fast response times (< 5 seconds)

### Deployment (You Just Did ✅):
- ✅ Webhooks registered via CLI OR
- ✅ Webhooks registered in Partners Dashboard OR  
- ✅ Webhooks registered programmatically (if app was installed)

---

## 🎯 If Checks Still Fail

**Most common issue:** Webhooks not visible in Partners Dashboard

**Fix:** Go to Partners Dashboard → Your App → **App Setup** → **Webhooks**

Check if you see:
- `customers/data_request`
- `customers/redact`
- `shop/redact`

If missing, add them manually with the URLs:
- `https://employeesuite-production.onrender.com/webhooks/customers/data_request`
- `https://employeesuite-production.onrender.com/webhooks/customers/redact`
- `https://employeesuite-production.onrender.com/webhooks/shop/redact`

---

## ✅ That's It!

Run the curl test above, then check Partners Dashboard. If both pass, you're good! 🎉
