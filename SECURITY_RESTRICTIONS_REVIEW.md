# 🔒 Security Restrictions Review

## Current Security Measures Analysis

### ✅ **Not Too Restrictive - OK**

1. **CSP `connect-src`** ✅
   - Allows: `'self'`, `https://*.myshopify.com`, `https://admin.shopify.com`, `https://api.stripe.com`
   - **Status**: ✅ Sufficient - covers all needed API calls
   - **Note**: Shopify webhooks come FROM Shopify to us (not blocked by CSP)

2. **CSP `form-action`** ✅
   - Allows: `'self'`, explicit app domain, `https://checkout.stripe.com`
   - **Status**: ✅ Fixed - now allows form submissions

3. **CSP `frame-src`** ✅
   - Allows: `https://checkout.stripe.com`, `https://js.stripe.com`
   - **Status**: ✅ OK - only need Stripe iframes

4. **Request Size Limit** ✅
   - 16MB max request size
   - **Status**: ✅ Reasonable - should be enough for most use cases

5. **Permissions-Policy** ⚠️ **POTENTIALLY RESTRICTIVE**
   - `payment=()` blocks payment APIs
   - **Status**: ⚠️ Could interfere with Stripe checkout iframe
   - **Note**: Since Stripe checkout runs in separate iframe, might be OK, but worth monitoring

6. **Referrer-Policy** ✅
   - `strict-origin-when-cross-origin`
   - **Status**: ✅ Standard, not too restrictive

7. **HSTS** ✅
   - Only in production
   - **Status**: ✅ Standard security practice

---

### ⚠️ **Potentially Too Restrictive**

#### 1. **Rate Limiting: 200 requests/hour** ⚠️ **TOO RESTRICTIVE**

**Current:**
- Global limit: **200 requests/hour** (~3 requests/minute)
- Applied to all routes by default

**Problem:**
- Users doing legitimate work might hit this:
  - Generating reports (multiple API calls)
  - Processing orders (multiple requests)
  - Dashboard interactions (AJAX requests)
  - Form submissions

**Recommendation:**
- Increase to **1000 requests/hour** (~16 requests/minute)
- Or exempt API endpoints that do heavy work
- Or use tiered limits (higher for authenticated users)

**Current Code:**
```python
# rate_limiter.py
default_limits=["200 per hour"]  # ← TOO LOW
```

**Suggested Fix:**
```python
default_limits=["1000 per hour"]  # More reasonable for legitimate users
```

---

#### 2. **CSP `script-src` - `'unsafe-eval'`** ⚠️ **SECURITY RISK**

**Current:**
- Allows `'unsafe-eval'` in embedded apps
- **Status**: ⚠️ Security risk, but might be needed for App Bridge

**Note:**
- App Bridge 3.x may require `'unsafe-eval'`
- If not needed, should remove it

**Check:** Test if app works without `'unsafe-eval'`

---

## Recommendations

### High Priority

1. **Increase rate limit** from 200/hour to 1000/hour
   - 200/hour is too restrictive for legitimate users
   - Could cause legitimate users to hit limits

### Medium Priority

2. **Review Permissions-Policy `payment=()`**
   - Test if Stripe checkout still works
   - If it does, leave it (security is good)
   - If not, might need to allow payment APIs in iframe

3. **Review `'unsafe-eval'` in CSP**
   - Test if App Bridge works without it
   - If possible, remove it for better security

### Low Priority

4. **Consider exempting certain routes from rate limiting:**
   - `/health` endpoint (monitoring)
   - `/api/generate_report` (long-running, legitimate)
   - Webhook endpoints (external, can't control rate)

---

## Action Items

- [ ] Increase rate limit to 1000/hour
- [ ] Test Stripe checkout with `payment=()` policy
- [ ] Test App Bridge without `'unsafe-eval'`
- [ ] Consider route-specific rate limits

