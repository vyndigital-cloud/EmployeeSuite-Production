# 🔍 WEBHOOK DEBUG - WHAT'S ACTUALLY BROKEN?

Let's find out exactly what Shopify is complaining about.

---

## ⚡ QUICK CHECKLIST (Do These NOW)

### 1. **Check if Webhooks are Registered in Partners Dashboard**

**Go to:** https://partners.shopify.com → Your App → **App Setup** → **Webhooks**

**Do you see these 3 webhooks listed?**
- `customers/data_request`
- `customers/redact`  
- `shop/redact`

**If NO:** Click "Add webhook" and add them manually with these URLs:
- `https://employeesuite-production.onrender.com/webhooks/customers/data_request`
- `https://employeesuite-production.onrender.com/webhooks/customers/redact`
- `https://employeesuite-production.onrender.com/webhooks/shop/redact`

**If YES:** Check if URLs match exactly (no trailing slashes, correct domain)

---

### 2. **Check SHOPIFY_API_SECRET in Render**

**Go to:** Render Dashboard → Your Service → **Environment**

**Is `SHOPIFY_API_SECRET` set?**
- If NO → Add it (get from Partners Dashboard → API credentials → Client secret)
- If YES → Check if it matches the **Client secret** (not API key) from Partners Dashboard

**Important:** The value must be the **Client secret**, not the API key!

---

### 3. **Test Webhook Endpoints Directly**

**Run these commands to test:**

```bash
# Test customers/data_request
curl -X POST https://employeesuite-production.onrender.com/webhooks/customers/data_request \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Hmac-Sha256: test123" \
  -d '{"test": "data"}'
```

**What do you get?**
- ✅ `{"error": "Invalid signature"}` with 401 = Endpoint exists, HMAC works
- ❌ `404 Not Found` = Endpoint doesn't exist (deployment issue)
- ❌ `500 Internal Server Error` = Code error (check Render logs)

**If you get 404:** The deployment might not have updated. Wait 2-3 minutes and try again, or manually redeploy in Render.

---

### 4. **Check Render Deployment Status**

**Go to:** Render Dashboard → Your Service → **Events**

**Is the latest deployment successful?**
- Look for the commit with "Optimize webhooks for Shopify compliance"
- Is it deployed? Does it show "Live" status?

**If deployment failed:** Check the logs for errors

---

### 5. **Check Render Logs for Webhook Requests**

**Go to:** Render Dashboard → Your Service → **Logs**

**Do you see any webhook requests?**
- Look for lines with "customers/data_request" or "Invalid webhook signature"
- If you see "Invalid webhook signature" → HMAC verification is running (good!)
- If you see errors → That's the problem

---

### 6. **Wait and Retry Shopify Checks**

**After making changes:**
1. Wait 2-3 minutes for deployment
2. Wait another 2-3 minutes for Shopify's system to re-check
3. Go to Partners Dashboard → Distribution → Click "Run" again

**Shopify's checks can take up to 48 hours to recognize changes (per their docs)**

---

## 🎯 MOST COMMON ISSUES

### Issue #1: Webhooks Not Registered in Partners Dashboard
**Fix:** Manually add them in Partners Dashboard → App Setup → Webhooks

### Issue #2: SHOPIFY_API_SECRET Missing/Wrong
**Fix:** Add/update in Render environment variables (must be Client secret, not API key)

### Issue #3: Deployment Not Updated
**Fix:** Wait for deployment to complete, or manually redeploy in Render

### Issue #4: Shopify's System Hasn't Re-checked Yet
**Fix:** Wait 48 hours (seriously, Shopify's automated checks can be slow)

---

## 🧪 ADVANCED DEBUG

### Check if HMAC Verification is Actually Working

Add this temporary debug endpoint (REMOVE AFTER TESTING):

```python
@app.route('/debug/test-hmac', methods=['POST'])
def test_hmac():
    from gdpr_compliance import verify_shopify_webhook
    hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
    raw_data = request.get_data(as_text=False)
    result = verify_shopify_webhook(raw_data, hmac_header)
    return jsonify({
        'has_hmac_header': hmac_header is not None,
        'has_secret': os.getenv('SHOPIFY_API_SECRET') is not None,
        'verification_result': result,
        'data_length': len(raw_data) if raw_data else 0
    })
```

**Test it:**
```bash
curl -X POST https://employeesuite-production.onrender.com/debug/test-hmac \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

**Should show:** `has_secret: true` (if SHOPIFY_API_SECRET is set)

---

## 📞 WHAT TO TELL ME

Tell me:
1. ✅ or ❌ Are webhooks registered in Partners Dashboard?
2. ✅ or ❌ Is SHOPIFY_API_SECRET set in Render?
3. What does the curl test return? (401, 404, 500, or something else?)
4. What error message does Shopify Partners Dashboard show? (screenshot if possible)

Then I can fix the exact problem! 🎯
