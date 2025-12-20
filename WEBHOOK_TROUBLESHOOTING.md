# 🔍 WEBHOOK TROUBLESHOOTING GUIDE

## Problem
Shopify Partners Dashboard shows:
- ❌ Provides mandatory compliance webhooks (Failed)
- ❌ Verifies webhooks with HMAC signatures (Failed)

---

## ✅ WHAT WE HAVE (Code Check)

### Webhook Endpoints:
- ✅ `/webhooks/customers/data_request` - Implemented in `gdpr_compliance.py`
- ✅ `/webhooks/customers/redact` - Implemented in `gdpr_compliance.py`
- ✅ `/webhooks/shop/redact` - Implemented in `gdpr_compliance.py`

### HMAC Verification:
- ✅ All 3 webhooks verify HMAC signatures
- ✅ Uses `SHOPIFY_API_SECRET` environment variable
- ✅ Uses `X-Shopify-Hmac-Sha256` header

### Code Registration:
- ✅ Webhooks listed in `app.json`
- ✅ `gdpr_bp` blueprint registered in `app.py`

---

## 🔍 TROUBLESHOOTING STEPS

### Step 1: Verify Environment Variable

**Check in Render Dashboard:**
```
SHOPIFY_API_SECRET = Your Shopify App API Secret
```

**How to get it:**
1. Go to Shopify Partners Dashboard
2. Your App → API credentials
3. Copy the "Client secret" (not the API key)

**If missing:**
- Shopify can't verify HMAC signatures
- Webhooks will fail security checks

---

### Step 2: Verify Webhooks are Registered in Shopify

**In Shopify Partners Dashboard:**
1. Go to: Your App → App Setup → Webhooks
2. Check these 3 webhooks exist:
   - `customers/data_request`
   - `customers/redact`
   - `shop/redact`
3. Check URLs match:
   - `https://employeesuite-production.onrender.com/webhooks/customers/data_request`
   - `https://employeesuite-production.onrender.com/webhooks/customers/redact`
   - `https://employeesuite-production.onrender.com/webhooks/shop/redact`

**If missing:**
- Add them manually OR
- Update `app.json` and re-submit app

---

### Step 3: Test Webhook Endpoints Manually

**Test 1: Check if endpoints exist (should return 401, not 404)**
```bash
curl -X POST https://employeesuite-production.onrender.com/webhooks/customers/data_request
# Should return: {"error": "Invalid signature"} (401)
# NOT: 404 Not Found
```

**Test 2: Check with proper HMAC (advanced)**
You'll need to generate a test HMAC signature - but first verify endpoints exist.

---

### Step 4: Check App Deployment

**Verify app is live:**
```bash
curl https://employeesuite-production.onrender.com/health
# Should return: {"status": "healthy", ...}
```

**If app is down:**
- Shopify can't test webhooks
- Fix deployment first

---

### Step 5: Check Logs in Render

**Look for:**
- Webhook requests from Shopify
- HMAC verification errors
- Missing `SHOPIFY_API_SECRET` errors

**In Render Dashboard:**
- Go to your service → Logs
- Filter for "webhook" or "GDPR"
- Look for error messages

---

## 🎯 COMMON ISSUES & FIXES

### Issue 1: Missing SHOPIFY_API_SECRET

**Symptoms:**
- HMAC verification always fails
- Logs show: "Invalid webhook signature"

**Fix:**
1. Get Client Secret from Shopify Partners → API credentials
2. Add to Render: `SHOPIFY_API_SECRET=your_secret_here`
3. Redeploy app

---

### Issue 2: Webhooks Not Registered

**Symptoms:**
- Dashboard shows webhooks as "Failed"
- No webhook delivery attempts in logs

**Fix:**
1. Go to Shopify Partners → Your App → App Setup → Webhooks
2. Add the 3 mandatory webhooks manually:
   - Topic: `customers/data_request`
   - URL: `https://employeesuite-production.onrender.com/webhooks/customers/data_request`
   - Format: JSON
   - Repeat for other 2 webhooks

---

### Issue 3: Wrong URL/Endpoint

**Symptoms:**
- 404 errors in logs
- Webhooks showing as "Failed"

**Fix:**
1. Verify your Render URL is correct
2. Check `app.json` has correct URLs
3. Update webhooks in Partners Dashboard to match

---

### Issue 4: HMAC Verification Failing

**Symptoms:**
- Logs show "Invalid signature"
- Webhooks return 401

**Fix:**
1. Verify `SHOPIFY_API_SECRET` matches the one in Partners Dashboard
2. Check the secret doesn't have extra spaces/characters
3. Ensure you're using the "Client Secret", not "API Key"

---

## 🔧 QUICK FIX CHECKLIST

Do these in order:

1. [ ] **Verify SHOPIFY_API_SECRET in Render**
   - Go to Render → Your Service → Environment
   - Check `SHOPIFY_API_SECRET` exists
   - Value should match Partners Dashboard → API credentials → Client Secret

2. [ ] **Verify App is Deployed & Running**
   - Check `https://employeesuite-production.onrender.com/health`
   - Should return 200 OK

3. [ ] **Verify Webhooks in Partners Dashboard**
   - Partners → Your App → App Setup → Webhooks
   - All 3 compliance webhooks should be listed
   - URLs should match your Render URL

4. [ ] **Test Webhook Endpoints**
   ```bash
   curl -X POST https://employeesuite-production.onrender.com/webhooks/customers/data_request
   # Should return 401 (invalid signature), NOT 404
   ```

5. [ ] **Check Render Logs**
   - Look for webhook requests
   - Look for HMAC errors
   - Check for missing environment variable errors

6. [ ] **Re-run Checks in Partners Dashboard**
   - Click "Run" button in Distribution section
   - Wait for checks to complete
   - Review results

---

## 📋 ENVIRONMENT VARIABLE CHECKLIST

**Required for Webhooks:**
- [ ] `SHOPIFY_API_SECRET` - From Partners Dashboard → API credentials → Client Secret
- [ ] `DATABASE_URL` - Auto from Render
- [ ] `SECRET_KEY` - Your Flask secret key

**How to get SHOPIFY_API_SECRET:**
1. Go to: https://partners.shopify.com
2. Your App → API credentials
3. Copy the "Client secret" value
4. Add to Render: `SHOPIFY_API_SECRET=paste_here`

---

## 🧪 TEST WEBHOOK ENDPOINTS

### Quick Test (Should return 401):
```bash
# Test 1: customers/data_request
curl -X POST https://employeesuite-production.onrender.com/webhooks/customers/data_request

# Expected: {"error": "Invalid signature"} with 401 status
# If 404: Endpoint doesn't exist (deployment issue)
# If 500: Code error (check logs)
```

---

## 🎯 EXPECTED BEHAVIOR

### When Shopify Tests Webhooks:

1. **Shopify sends test request:**
   - POST to your webhook URL
   - Includes `X-Shopify-Hmac-Sha256` header
   - Includes test JSON data

2. **Your app should:**
   - Verify HMAC signature using `SHOPIFY_API_SECRET`
   - Return 200 OK if valid
   - Return 401 if invalid signature

3. **If successful:**
   - Dashboard shows ✅ green checkmark
   - Checks pass

---

## 🚨 IF STILL FAILING

**Next steps:**
1. Check Render logs for actual error messages
2. Test webhook endpoints manually (see tests above)
3. Verify `SHOPIFY_API_SECRET` is correct
4. Make sure webhooks are registered in Partners Dashboard (not just in app.json)
5. Try re-registering webhooks manually in Partners Dashboard

**Most common issue:** Missing or incorrect `SHOPIFY_API_SECRET` environment variable.

---

## ✅ SUCCESS CRITERIA

You'll know it's working when:
- ✅ Dashboard shows green checkmarks for both webhook checks
- ✅ Test requests return 401 (not 404)
- ✅ Render logs show successful HMAC verification
- ✅ No errors in logs about missing SHOPIFY_API_SECRET
