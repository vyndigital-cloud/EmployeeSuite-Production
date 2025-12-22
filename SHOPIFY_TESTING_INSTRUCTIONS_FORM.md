# 📝 Shopify App Store - Testing Instructions (Copy & Paste)

## For "Testing Instructions" Field (2800 characters max)

Copy this into the "Instruction notes" field:

---

**To test Employee Suite:**

1. **Create test account:**
   - Go to: https://employeesuite-production.onrender.com/register
   - Email: shopify-review@test.com
   - Password: TestAccount123!
   - Click "Start Free Trial"

2. **Connect Shopify store:**
   - After login, go to Settings → Connect Shopify Store
   - Enter your development store domain (e.g., yourstore.myshopify.com)
   - Click "Connect with Shopify"
   - Complete OAuth flow
   - Store should show as "Connected"

3. **Test Order Processing:**
   - In your development store, create 2-3 test orders with status "Unfulfilled"
   - In Employee Suite dashboard, click "View Orders →"
   - Verify unfulfilled orders display correctly

4. **Test Inventory Management:**
   - In your development store, add products with different stock levels (0, 5, 20)
   - In Employee Suite dashboard, click "Check Inventory →"
   - Verify products display with correct stock levels
   - Test search and filter functionality
   - Click "📥 Export CSV" to test export

5. **Test Revenue Analytics:**
   - In Employee Suite dashboard, click "Generate Report →"
   - Verify report shows total revenue, orders, and product breakdown
   - Click "📥 Export CSV" (top right) to test export

6. **Test Subscription:**
   - Click "Subscribe" button
   - Use Stripe test card: 4242 4242 4242 4242
   - Complete checkout
   - Verify subscription activates

**Test Account Credentials:**
- Email: shopify-review@test.com
- Password: TestAccount123!

**App URL:** https://employeesuite-production.onrender.com

---

## Character Count: ~1,200 / 2,800 ✅

---

## Alternative Shorter Version (if needed):

**To test Employee Suite:**

1. Register at https://employeesuite-production.onrender.com/register
   - Email: shopify-review@test.com
   - Password: TestAccount123!

2. Connect Shopify store via Settings → Connect Shopify Store

3. Test features:
   - Order Processing: Create unfulfilled orders, verify they display
   - Inventory: Add products, verify stock levels and CSV export
   - Revenue: Generate report, verify data and CSV export

4. Test subscription with Stripe test card: 4242 4242 4242 4242

**Credentials:** shopify-review@test.com / TestAccount123!

---

## Character Count: ~500 / 2,800 ✅

