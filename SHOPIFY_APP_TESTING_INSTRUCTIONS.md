# 🧪 Shopify App Store - Complete Testing Instructions

**Purpose:** Test your app thoroughly before submitting to Shopify App Store  
**Time Required:** 30-45 minutes  
**Status:** ✅ Ready to test

---

## 📋 Pre-Testing Checklist

### Before You Start:
- [ ] App is deployed to production (`employeesuite-production.onrender.com`)
- [ ] All environment variables are set in Render
- [ ] Test account created: `shopify-review@test.com` / `TestAccount123!`
- [ ] Development store created in Shopify Partners
- [ ] App is installed in development store (via OAuth)

---

## 1. 🔐 OAuth Installation Flow Test

### Test Steps:
1. **Go to your development store admin**
2. **Navigate to Apps** → **App and sales channel settings**
3. **Click "Develop apps"** → Select your app
4. **Click "Install app"** (or use the OAuth URL)

### What to Verify:
- [ ] OAuth redirect works correctly
- [ ] You're redirected to your app's callback URL
- [ ] Store is saved to database
- [ ] You're automatically logged in
- [ ] Dashboard loads successfully
- [ ] Store connection shows as "Connected" in Settings

### Expected Result:
✅ Smooth installation flow, store connected, user logged in

---

## 2. 📦 Order Processing Test

### Test Steps:
1. **Create test orders in your development store:**
   - Go to Orders → Create order
   - Add products, set order status to "Unfulfilled"
   - Create 2-3 test orders
2. **In your app dashboard, click "View Orders →"**
3. **Verify orders appear**

### What to Verify:
- [ ] Pending/unfulfilled orders display correctly
- [ ] Order details show (order number, customer, amount)
- [ ] Fulfilled orders are NOT shown
- [ ] Error message displays if store not connected
- [ ] "Connect Store" button works in error state

### Expected Result:
✅ All unfulfilled orders display with correct information

---

## 3. 📊 Inventory Management Test

### Test Steps:
1. **In your development store, add products with different stock levels:**
   - Product A: 0 stock (critical)
   - Product B: 5 stock (low stock)
   - Product C: 20 stock (good stock)
2. **In your app dashboard, click "Check Inventory →"**
3. **Test search and filter:**
   - Search by product name
   - Filter by stock level (Critical/Low/Good)
4. **Test CSV export:**
   - Click "📥 Export CSV"
   - Verify file downloads
   - Open in Excel/Sheets to verify data

### What to Verify:
- [ ] All products display
- [ ] Stock levels are correct
- [ ] Color coding works (Red: ≤0, Orange: 1-9, Green: 10+)
- [ ] Products sorted by priority (lowest stock first)
- [ ] Search works (instant, no reload)
- [ ] Filter works (Critical/Low/Good)
- [ ] CSV export works and contains correct data
- [ ] Error message displays if store not connected

### Expected Result:
✅ Inventory displays correctly, search/filter work, CSV exports properly

---

## 4. 💰 Revenue Analytics Test

### Test Steps:
1. **Ensure you have orders with products in your development store**
2. **In your app dashboard, click "Generate Report →"**
3. **Verify report displays:**
   - Total revenue
   - Total orders
   - Top products breakdown
   - Percentages calculated correctly
4. **Test CSV export:**
   - Click "📥 Export CSV" (top right, aligned with title)
   - Verify file downloads
   - Open in Excel/Sheets to verify data

### What to Verify:
- [ ] Report generates successfully
- [ ] Total revenue is correct
- [ ] Total orders count is correct
- [ ] Product breakdown shows top products
- [ ] Percentages are calculated correctly
- [ ] CSV export button is in top right (aligned with title)
- [ ] CSV export works and contains correct data
- [ ] Error message displays if store not connected

### Expected Result:
✅ Report generates with accurate data, CSV export works

---

## 5. 🔔 Webhook Testing

### Test Steps:

#### A. Test App Uninstall Webhook:
1. **In development store admin:**
   - Go to Apps → Your app
   - Click "Uninstall"
2. **Verify in your app:**
   - Store is marked as inactive
   - `uninstalled_at` timestamp is set

#### B. Test GDPR Compliance Webhooks:
1. **In Shopify Partners Dashboard:**
   - Go to Your App → App Setup → Webhooks
   - Find each webhook and click "Send test webhook"
   - Test these 3 webhooks:
     - `customers/data_request`
     - `customers/redact`
     - `shop/redact`

### What to Verify:
- [ ] All webhooks receive requests
- [ ] All webhooks return 200 OK
- [ ] HMAC signatures are verified
- [ ] No errors in logs
- [ ] App uninstall marks store as inactive

### Expected Result:
✅ All webhooks respond correctly with 200 OK

---

## 6. 💳 Billing/Subscription Test

### Test Steps:
1. **Log in with test account** (`shopify-review@test.com`)
2. **Go to Settings → Subscription** (or click "Subscribe" button)
3. **Test subscription flow:**
   - Click "Subscribe Now"
   - Verify Stripe checkout opens
   - Use test card: `4242 4242 4242 4242`
   - Complete checkout
4. **Verify subscription:**
   - User is marked as subscribed
   - Access is granted
   - Subscription page shows active status

### What to Verify:
- [ ] Subscription page loads
- [ ] Stripe checkout works
- [ ] Payment processing works
- [ ] User status updates to "subscribed"
- [ ] Access is granted after payment
- [ ] Trial period works (7 days)

### Expected Result:
✅ Subscription flow works end-to-end

---

## 7. 🔒 Security & Access Control Test

### Test Steps:

#### A. Test Authentication:
1. **Log out**
2. **Try to access `/dashboard` directly**
3. **Verify redirect to login**

#### B. Test Trial Expiration:
1. **Create a test user with expired trial** (manually set `trial_ends_at` in database)
2. **Try to access dashboard**
3. **Verify redirect to billing/subscribe page**

#### C. Test Access Control:
1. **With store NOT connected:**
   - Try to process orders
   - Try to check inventory
   - Try to generate report
2. **Verify error messages display correctly**

### What to Verify:
- [ ] Unauthenticated users redirected to login
- [ ] Trial-expired users redirected to billing
- [ ] Error messages display when store not connected
- [ ] "Connect Store" buttons work in error states
- [ ] All protected routes require authentication

### Expected Result:
✅ All security and access controls work correctly

---

## 8. 📱 UI/UX Test

### Test Steps:
1. **Navigate through all pages:**
   - Home page
   - Login page
   - Sign up page
   - Dashboard
   - Settings
   - Subscription page
2. **Test on different screen sizes:**
   - Desktop (1920x1080)
   - Tablet (768px)
   - Mobile (375px)

### What to Verify:
- [ ] All pages load correctly
- [ ] Buttons work and have proper hover states
- [ ] Forms submit correctly
- [ ] Error messages display properly
- [ ] Success messages display properly
- [ ] Loading states work (spinners on buttons)
- [ ] Responsive design works on mobile
- [ ] Sign up page matches site style
- [ ] CSV export button is in top right of revenue report

### Expected Result:
✅ All UI elements work correctly, responsive design works

---

## 9. 🐛 Error Handling Test

### Test Steps:

#### A. Test Invalid Store Connection:
1. **Manually enter invalid store domain**
2. **Try to connect**
3. **Verify error message displays**

#### B. Test API Failures:
1. **Temporarily break store connection** (change access token)
2. **Try to process orders**
3. **Verify error message displays**

#### C. Test Network Errors:
1. **Disconnect internet**
2. **Try to load dashboard**
3. **Verify graceful error handling**

### What to Verify:
- [ ] Error messages are user-friendly
- [ ] Error messages include action buttons ("Connect Store", "Log In")
- [ ] Errors are logged properly
- [ ] App doesn't crash on errors
- [ ] Users can recover from errors

### Expected Result:
✅ All errors handled gracefully with helpful messages

---

## 10. 📊 Performance Test

### Test Steps:
1. **Load dashboard with connected store**
2. **Measure load times:**
   - Dashboard initial load
   - Order processing
   - Inventory check
   - Report generation
3. **Test with multiple products/orders**

### What to Verify:
- [ ] Dashboard loads in < 3 seconds
- [ ] API calls complete in < 5 seconds
- [ ] No memory leaks
- [ ] Database queries are optimized
- [ ] Large datasets (100+ products) load reasonably

### Expected Result:
✅ App performs well under normal load

---

## 11. 🔍 Final Checklist Before Submission

### Code Quality:
- [ ] No console errors in browser
- [ ] No errors in server logs
- [ ] All features work as expected
- [ ] All error states handled
- [ ] All success states work

### Shopify Requirements:
- [ ] OAuth flow works
- [ ] All 3 GDPR webhooks work
- [ ] App uninstall webhook works
- [ ] Session token verification works (if embedded)
- [ ] Billing integration works

### User Experience:
- [ ] All pages load correctly
- [ ] All buttons work
- [ ] All forms submit correctly
- [ ] Error messages are helpful
- [ ] Success messages are clear
- [ ] Mobile responsive

### Documentation:
- [ ] Test account credentials ready
- [ ] Screencast video created
- [ ] All app store listing fields filled
- [ ] Support email configured
- [ ] Privacy policy and terms published

---

## 🎯 Test Results Template

After testing, document your results:

```
✅ OAuth Installation: PASS / FAIL
✅ Order Processing: PASS / FAIL
✅ Inventory Management: PASS / FAIL
✅ Revenue Analytics: PASS / FAIL
✅ Webhooks: PASS / FAIL
✅ Billing/Subscription: PASS / FAIL
✅ Security & Access: PASS / FAIL
✅ UI/UX: PASS / FAIL
✅ Error Handling: PASS / FAIL
✅ Performance: PASS / FAIL
```

---

## 🚨 Common Issues & Fixes

### Issue: "Store not connected" error
**Fix:** Verify OAuth flow completed, check database for store record

### Issue: Webhooks not receiving requests
**Fix:** Verify webhooks are registered in Partners Dashboard, check HMAC secret

### Issue: CSV export not working
**Fix:** Check session data, verify export endpoint is accessible

### Issue: Subscription not activating
**Fix:** Check Stripe webhook, verify webhook secret is correct

### Issue: Error messages not displaying
**Fix:** Check browser console, verify HTML is being inserted correctly

---

## ✅ Ready to Submit?

If all tests pass:
1. ✅ Create test account
2. ✅ Record screencast video
3. ✅ Complete app store listing
4. ✅ Submit for review! 🚀

---

## 📞 Need Help?

If you encounter issues during testing:
1. Check server logs in Render
2. Check browser console for errors
3. Verify environment variables are set
4. Test in incognito mode (clear cache)

**Good luck with your submission!** 🎉







