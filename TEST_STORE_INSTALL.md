# 🧪 TEST STORE INSTALLATION GUIDE

## Quick Steps

### 1. Create/Use Test Store

If you don't have a test store:
- Go to **Shopify Partners Dashboard** → **Stores** → **Add store** → **Development store**
- Create a new development store

---

### 2. Install Your App

**Option A: Via App URL (Easiest)**

Go to this URL in your browser (replace `YOUR-TEST-STORE` with your actual shop domain):
```
https://employeesuite-production.onrender.com/install?shop=YOUR-TEST-STORE.myshopify.com
```

**Example:**
```
https://employeesuite-production.onrender.com/install?shop=myteststore.myshopify.com
```

This will:
1. Redirect you to Shopify OAuth
2. Ask you to authorize the app
3. Redirect back to your app
4. **Automatically register all 3 compliance webhooks** ✅

**Option B: Via Partners Dashboard**
1. Go to **Partners Dashboard** → Your App → **Development stores**
2. Click on your test store
3. Go to **Apps** → Find your app → Click **Install**

---

### 3. What Happens Automatically

When the app installs, the OAuth callback will:
1. ✅ Create user account
2. ✅ Store Shopify credentials  
3. ✅ **Automatically register all 3 compliance webhooks** (via `register_compliance_webhooks()` function)
4. ✅ Log you in

**Check Render logs** to see webhook registration messages:
```
Successfully registered compliance webhook: customers/data_request for shop YOUR-TEST-STORE.myshopify.com
Successfully registered compliance webhook: customers/redact for shop YOUR-TEST-STORE.myshopify.com
Successfully registered compliance webhook: shop/redact for shop YOUR-TEST-STORE.myshopify.com
```

---

### 4. Verify Webhooks Registered

**In Shopify Admin:**
1. Go to your test store admin
2. **Settings** → **Notifications** → **Webhooks**
3. You should see the 3 compliance webhooks listed:
   - `customers/data_request`
   - `customers/redact`
   - `shop/redact`

All pointing to: `https://employeesuite-production.onrender.com/webhooks/...`

---

### 5. Re-run Automated Checks

**After installation:**
1. Wait 2-3 minutes (let Shopify sync)
2. Go to **Partners Dashboard** → Your App → **Distribution**
3. Click **"Run"** to re-run automated checks
4. ✅ Checks should now pass!

---

## ✅ What This Proves

- ✅ Code works correctly
- ✅ Webhooks register automatically
- ✅ HMAC verification works
- ✅ Shopify can see the webhooks are registered

**This is the fastest way to get automated checks to pass!**
