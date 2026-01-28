# Testing Instructions for Shopify App Reviewer

## Test Account Credentials
- **Email:** shopify-review@test.com
- **Password:** TestAccount123!

## App URL
https://employeesuite-production.onrender.com

---

## Test 1: Install the App (OAuth Flow)

1. From your development store admin, go to **Apps** > **Add apps**
2. Search for or select **EmployeeSuite**
3. Click **Install app**
4. You will be redirected to the app and logged in automatically
5. The dashboard should display with your store connected

**Expected:** Smooth OAuth flow, automatic login, dashboard loads

---

## Test 2: View Pending Orders

1. In your development store, create 2-3 test orders (leave as "Unfulfilled")
2. In the app dashboard, click **"View Orders"**
3. Verify all unfulfilled orders appear with order number, customer name, and amount

**Expected:** All pending orders display correctly

---

## Test 3: Check Inventory

1. In the app dashboard, click **"Check Inventory"**
2. All products from your store should appear sorted by stock level
3. Test the search bar by typing a product name
4. Test filters: Critical (0 stock), Low (1-9), Good (10+)
5. Click **"Export CSV"** - a file should download

**Expected:** Products display with correct stock levels, search/filter work, CSV downloads

---

## Test 4: Generate Revenue Report

1. In the app dashboard, click **"Generate Report"**
2. Report shows total revenue, order count, and top products
3. Click **"Export CSV"** to download the report

**Expected:** Report generates with accurate data, CSV exports

---

## Test 5: Verify GDPR Webhooks

The app responds to all mandatory GDPR webhooks:
- `customers/data_request` - Returns 200 OK
- `customers/redact` - Returns 200 OK
- `shop/redact` - Returns 200 OK

These can be tested via the Partners Dashboard webhook test feature.

---

## Test 6: Uninstall/Reinstall

1. Uninstall the app from your development store
2. Reinstall the app
3. Verify OAuth flow works correctly on reinstall

**Expected:** Clean uninstall, successful reinstall

---

## Support

If you encounter any issues during testing, please contact: support@employeesuite.com
