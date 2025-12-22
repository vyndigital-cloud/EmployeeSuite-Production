# 🚀 Complete Shopify App Migration Checklist
## Dev Store → Partners Account Transfer

**Purpose:** Migrate app ownership to enable billing API and App Store listing

---

## 📋 PRE-MIGRATION CHECKLIST

### ✅ Before You Start
- [ ] You have a Shopify Partners account (https://partners.shopify.com)
- [ ] You know your Partners account email
- [ ] You have access to your dev store admin
- [ ] You have a backup of your current app credentials
- [ ] You know your app's current name and purpose

---

## 🔧 STEP 1: Create App in Partners Dashboard

### 1.1 Access Partners Dashboard
- [ ] Go to https://partners.shopify.com
- [ ] Log in with your Partners account
- [ ] Navigate to **Apps** in the left sidebar

### 1.2 Create New App
- [ ] Click **"Create app"** button
- [ ] Choose **"Public app"** (for App Store) OR **"Custom app"** (for specific stores)
- [ ] Enter your app details:
  - [ ] **App name:** `Employee Suite` (or your preferred name)
  - [ ] **App URL:** `https://employeesuite-production.onrender.com` (your production URL)
  - [ ] **Allowed redirection URL(s):** 
    - [ ] `https://employeesuite-production.onrender.com/auth/shopify/callback`
    - [ ] `https://employeesuite-production.onrender.com/settings/shopify/callback`
  - [ ] **App description:** Brief description of what your app does
  - [ ] **App icon:** Upload your app icon (optional but recommended)
  - [ ] **App website:** Your website URL (if applicable)

### 1.3 Configure App Settings
- [ ] **API scopes:** Select required scopes:
  - [ ] `read_orders`
  - [ ] `read_products`
  - [ ] `read_inventory`
  - [ ] `read_customers` (if needed)
  - [ ] `write_products` (if you modify inventory)
  - [ ] Any other scopes your app uses
- [ ] **Billing:** Enable billing API (required for subscriptions)
- [ ] **Webhooks:** Configure webhook endpoints:
  - [ ] `app/uninstalled` → `https://employeesuite-production.onrender.com/webhooks/shopify/uninstall`
  - [ ] `customers/data_request` → `https://employeesuite-production.onrender.com/webhooks/shopify/customers/data_request`
  - [ ] `customers/redact` → `https://employeesuite-production.onrender.com/webhooks/shopify/customers/redact`
  - [ ] `shop/redact` → `https://employeesuite-production.onrender.com/webhooks/shopify/shop/redact`
  - [ ] Any other webhooks you use

---

## 🔑 STEP 2: Get New API Credentials

### 2.1 Copy API Credentials
- [ ] Go to **App setup** tab in Partners dashboard
- [ ] Copy **API key** (Client ID)
- [ ] Copy **API secret key** (Client Secret)
- [ ] Save these securely (you'll need them in Step 3)

### 2.2 Verify App Details
- [ ] **App name:** Matches what you want users to see
- [ ] **App URL:** Points to your production server
- [ ] **Redirect URLs:** All callback URLs are listed
- [ ] **Scopes:** All required permissions are granted
- [ ] **Billing:** Enabled and configured

---

## 💻 STEP 3: Update Your Code

### 3.1 Update Environment Variables
- [ ] Update `SHOPIFY_API_KEY` in your deployment platform (Render):
  ```bash
  SHOPIFY_API_KEY=<new_partners_api_key>
  ```
- [ ] Update `SHOPIFY_API_SECRET` in your deployment platform:
  ```bash
  SHOPIFY_API_SECRET=<new_partners_api_secret>
  ```
- [ ] Update `SHOPIFY_APP_URL` if it changed:
  ```bash
  SHOPIFY_APP_URL=https://employeesuite-production.onrender.com
  ```

### 3.2 Update Code Files (if hardcoded)
- [ ] Check `app.py` for any hardcoded API keys
- [ ] Check `shopify_oauth.py` for API key references
- [ ] Check `billing.py` for API key references
- [ ] Update any hardcoded credentials to use environment variables

### 3.3 Verify OAuth Flow
- [ ] Check `shopify_oauth.py` uses `SHOPIFY_API_KEY` from environment
- [ ] Verify redirect URL matches Partners dashboard
- [ ] Test OAuth callback URL is correct

---

## 🧪 STEP 4: Test the Migration

### 4.1 Test OAuth Installation
- [ ] Uninstall app from test store (if installed)
- [ ] Install app using new Partners credentials
- [ ] Verify OAuth flow completes successfully
- [ ] Check that store is saved in database

### 4.2 Test Billing API
- [ ] Go to subscribe page in your app
- [ ] Click "Subscribe" button
- [ ] Verify billing charge creation works
- [ ] Check that "app owned by a shop" error is gone
- [ ] Verify charge appears in Shopify admin

### 4.3 Test App Functionality
- [ ] Test order processing
- [ ] Test inventory updates
- [ ] Test report generation
- [ ] Verify all API calls work correctly

---

## 📝 STEP 5: Update App Store Listing (If Public App)

### 5.1 App Store Information
- [ ] **App name:** Final name for App Store
- [ ] **Short description:** 1-2 sentence summary
- [ ] **Long description:** Detailed app features
- [ ] **App icon:** High-quality icon (512x512px recommended)
- [ ] **Screenshots:** App screenshots (at least 3)
- [ ] **Support email:** Your support email
- [ ] **Privacy policy URL:** Link to your privacy policy
- [ ] **Terms of service URL:** Link to your terms

### 5.2 Pricing Information
- [ ] **Pricing model:** Recurring charge / One-time / Usage-based
- [ ] **Price:** Your subscription price
- [ ] **Trial period:** 7 days (or your preference)
- [ ] **Billing description:** What users are charged for

### 5.3 Categories & Tags
- [ ] Select appropriate app categories
- [ ] Add relevant tags for discoverability
- [ ] Choose target audience

---

## 🔄 STEP 6: Handle Existing Installations

### 6.1 Notify Existing Users (If Any)
- [ ] Send email to existing users about migration
- [ ] Explain they may need to reinstall
- [ ] Provide migration instructions if needed

### 6.2 Migration Strategy
- [ ] **Option A:** Keep old app running until all users migrate
- [ ] **Option B:** Force reinstall (users install new app)
- [ ] **Option C:** Automatic migration (if possible)

---

## ✅ STEP 7: Final Verification

### 7.1 Production Checklist
- [ ] All environment variables updated in Render
- [ ] App deployed with new credentials
- [ ] OAuth flow works in production
- [ ] Billing API works in production
- [ ] Webhooks are receiving events
- [ ] No "app owned by a shop" errors

### 7.2 Monitoring
- [ ] Check Render logs for errors
- [ ] Monitor Sentry for any issues
- [ ] Verify database connections work
- [ ] Test all API endpoints

### 7.3 Documentation
- [ ] Update README with new setup instructions
- [ ] Document new API credentials location
- [ ] Update deployment guide if needed

---

## 🚨 TROUBLESHOOTING

### Common Issues

**Issue:** "App owned by a shop" error still appears
- **Solution:** Verify you're using Partners API credentials, not dev store credentials

**Issue:** OAuth redirect fails
- **Solution:** Check redirect URLs match exactly in Partners dashboard

**Issue:** Billing API returns 422 error
- **Solution:** Ensure billing is enabled in Partners dashboard → App setup → Billing

**Issue:** Webhooks not receiving events
- **Solution:** Verify webhook URLs are correct and accessible (HTTPS required)

**Issue:** App doesn't appear in Partners dashboard
- **Solution:** You may need to create a new app (transfer not always available)

---

## 📞 SUPPORT RESOURCES

- **Shopify Partners Help:** https://help.shopify.com/en/partners
- **Partners Dashboard:** https://partners.shopify.com
- **API Documentation:** https://shopify.dev/docs/api
- **Billing API Guide:** https://shopify.dev/docs/apps/billing

---

## ✅ MIGRATION COMPLETE CHECKLIST

- [ ] App created in Partners dashboard
- [ ] API credentials updated in environment variables
- [ ] Code deployed with new credentials
- [ ] OAuth installation tested and working
- [ ] Billing API tested and working
- [ ] All app features tested
- [ ] No errors in logs
- [ ] App Store listing updated (if public app)
- [ ] Existing users notified (if applicable)

---

**Migration Status:** ⬜ Not Started | ⬜ In Progress | ⬜ Complete

**Date Completed:** _______________

**Notes:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

