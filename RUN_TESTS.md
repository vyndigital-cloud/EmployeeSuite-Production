# 🧪 HOW TO RUN AUTOMATED TESTS

## Quick Test (Verify Shopify Sync)

**Run this to verify your app fetches all orders correctly:**

```bash
cd /Users/essentials/Documents/1EmployeeSuite-FIXED
source venv/bin/activate

# Set your Shopify credentials (or add to .env file)
export SHOPIFY_URL="yourstore.myshopify.com"
export SHOPIFY_TOKEN="shpat_xxxxx"

# Run the test
python3 test_shopify_sync.py
```

**What It Tests:**
1. ✅ Pagination fetches ALL orders (not just first 250)
2. ✅ Revenue calculation matches Shopify
3. ✅ Order processing shows correct pending/unfulfilled orders
4. ✅ Inventory fetches all products

**Expected Output:**
```
🧪 Shopify API Integration Test
============================================================
🔍 Testing Shopify API connection to: yourstore.myshopify.com
============================================================

1️⃣ Testing Revenue Report Pagination:
------------------------------------------------------------
   Page 1: Fetched 250 orders (Total: 250)
   Page 2: Fetched 5 orders (Total: 255)

✅ Pagination Test Results:
   Total Orders Fetched: 255
   Total Revenue: $12,345.67
```

**If Test Passes:**
- ✅ Your app is fetching all orders correctly
- ✅ Pagination is working
- ✅ Revenue matches Shopify

**If Test Fails:**
- ❌ Check Shopify credentials
- ❌ Check API permissions
- ❌ Check Render logs for errors

---

## Compare With Shopify Admin

**After running test:**

1. **Open Shopify Admin:**
   - Go to Orders → Filter: Paid
   - Count total orders
   - Add up total revenue

2. **Compare with test output:**
   - Order count should match
   - Revenue should match exactly

3. **If they match:** ✅ Everything works!
4. **If they don't match:** Check pagination logic

---

## Run Tests Before Every Deploy

**Add to your workflow:**
```bash
# Before deploying:
python3 test_shopify_sync.py

# If tests pass:
git push origin main

# If tests fail:
# Fix issues first, then deploy
```

---

## What The Test Checks

### ✅ Pagination Verification
- Fetches orders in batches of 250
- Uses `since_id` for next page
- Continues until all orders fetched
- Verifies total count matches Shopify

### ✅ Revenue Calculation
- Sums all order totals
- Matches Shopify Admin revenue
- Handles edge cases (0 orders, 1 order, etc.)

### ✅ Order Processing
- Fetches pending payment orders
- Fetches unfulfilled orders
- Deduplicates correctly
- Shows only orders needing action

### ✅ Inventory
- Fetches all products
- Counts variants correctly
- Identifies low stock items
- Matches Shopify product count

---

## Troubleshooting

**Test fails with "No SHOPIFY_TOKEN":**
```bash
# Add to .env file:
SHOPIFY_URL=yourstore.myshopify.com
SHOPIFY_TOKEN=shpat_xxxxx
```

**Test shows wrong order count:**
- Check if pagination is working (look for multiple "Page X" messages)
- Verify `since_id` pagination is being used
- Check Render logs for pagination errors

**Revenue doesn't match:**
- Verify all orders are being fetched (check pagination)
- Check if orders are being filtered correctly
- Verify order totals match Shopify Admin

---

**Last Updated:** December 5, 2024

