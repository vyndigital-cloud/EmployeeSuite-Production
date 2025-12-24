# ✅ Shopify Technical Criteria Checklist

## 🔍 Based on Partners Dashboard Requirements

### 1. "Is embedded in the Shopify admin" ✅

#### ✅ Enable app embedding
- **Status:** ✅ DONE
- **Location:** `app.json` line 12: `"embedded": true`
- **CSP Headers:** ✅ Fixed - Includes shop domain in frame-ancestors
- **Verification:** App can be loaded in iframe

#### ✅ Use session token authentication  
- **Status:** ✅ DONE
- **Location:** `session_token_verification.py`
- **Implementation:** 
  - `@verify_session_token` decorator exists
  - App Bridge fetches tokens via `getSessionToken()`
  - All API routes use session tokens in embedded mode
- **Verification:** Session tokens verified on all API calls

#### ⚠️ Use the latest version of App Bridge on every page
- **Status:** ⚠️ PARTIAL - Needs fixing
- **Current Issues:**
  - ✅ Dashboard (`app.py`): Uses versioned `app-bridge/3.7.0/app-bridge.js`
  - ❌ Billing/Subscribe (`billing.py`): Uses unversioned `app-bridge.js` (line 26, 195)
  - ❌ App Bridge integration (`app_bridge_integration.py`): Uses unversioned `app-bridge.js` (line 21)
- **Action Required:** Update all pages to use versioned App Bridge

---

### 2. Performance Criteria ⚠️

#### ⚠️ Meets benchmarks for 2025 Core Web Vitals
- **Status:** ⚠️ NEEDS TESTING
- **Requirements:**
  - LCP < 2.5 seconds
  - CLS < 0.1
  - INP < 200ms
- **Action Required:** Test with Shopify's performance tools after deployment

#### ⚠️ Minimizes impact on storefront loading speed
- **Status:** ⚠️ N/A (Admin app, doesn't affect storefront)
- **Note:** This is typically for storefront extensions, not admin apps

---

### 3. Design and Functionality

#### ✅ Uses Shopify design guidelines
- **Status:** ✅ DONE
- **Evidence:** Using Shopify Polaris-style design system

#### ⚠️ Is a well integrated app
- **Status:** ✅ DONE
- **Evidence:** Proper OAuth, webhooks, billing integration

#### ✅ Doesn't use Asset API
- **Status:** ✅ DONE
- **Verification:** No Asset API usage in codebase

#### ⚠️ Uses theme extensions to add storefront functionality
- **Status:** ⚠️ N/A
- **Note:** This app is admin-only, no storefront functionality

---

## 🚨 CRITICAL FIXES NEEDED

### Fix 1: Update App Bridge Version on All Pages

**Files to update:**
1. `billing.py` - Lines 26, 195 (unversioned → versioned)
2. `app_bridge_integration.py` - Line 21 (unversioned → versioned)

**Change from:**
```javascript
<script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
```

**Change to:**
```javascript
<script src="https://cdn.shopify.com/shopifycloud/app-bridge/3.7.0/app-bridge.js"></script>
```

---

## ✅ WHAT'S ALREADY DONE

1. ✅ App embedding enabled (`app.json`)
2. ✅ CSP frame-ancestors configured (includes shop domain)
3. ✅ Session token authentication implemented
4. ✅ App Bridge used (versioned on dashboard, needs fixing on other pages)
5. ✅ Security headers configured
6. ✅ GDPR compliance webhooks implemented
7. ✅ Billing API integrated

---

## 📋 NEXT STEPS

1. **Fix App Bridge versions** - Update billing.py and app_bridge_integration.py
2. **Deploy fixes** - Push to GitHub and deploy to Render
3. **Test in Shopify admin** - Use the app to generate session data
4. **Wait for automated checks** - Shopify checks every 2 hours
5. **Verify all checkboxes** - Should turn green after using the app

---

## 🎯 EXPECTED RESULT

After fixes and deployment:
- ✅ "Enable app embedding" - Green
- ✅ "Use session token authentication" - Green  
- ✅ "Use the latest version of App Bridge on every page" - Green
- ✅ Other criteria should pass (or be N/A for admin-only apps)

