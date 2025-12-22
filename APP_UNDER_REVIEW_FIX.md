# 🔧 FIX: "App Under Review" Error

## The Problem

Your screenshot shows:
> **"This app is under review"**  
> "Employee Suite needs to be reviewed by Shopify before it can be installed."

This means the app was **submitted for review** and Shopify is reviewing it. While under review, you **cannot install it in test stores**.

---

## ✅ SOLUTION: Change App Status to Development

To test the app, you need to change it back to **Development** status (which allows testing).

### Steps:

1. Go to **Shopify Partners Dashboard** → **Apps**
2. Click on **"Employee Suite"**
3. Go to **"Overview"** tab
4. Look for **"App status"** or **"Distribution"** section
5. Click **"Unpublish"** or **"Remove from review"** (button name varies)
6. This will change status to **Development**

**OR:**

1. Go to **Shopify Partners Dashboard** → Your App → **Distribution**
2. If there's a pending submission, you can **"Withdraw"** or **"Cancel"** it
3. This allows testing in development mode

---

## ✅ After Changing to Development

Once the app is in **Development** status:

1. Go back to your test store
2. Try installing again
3. Should work now! ✅

**Development apps can be installed in:**
- Your own development stores
- Test stores you create
- Stores you have access to

---

## 🎯 Why This Happened

If you submitted the app to the Shopify App Store, Shopify automatically puts it "under review" and locks it until they approve/reject it. During this time, **no one can install it** (even you).

---

## 💡 For Testing Webhooks

Since you just want to test webhooks and compliance checks:

1. **Change app to Development** (steps above)
2. Install in test store
3. Webhooks will register automatically
4. Run compliance checks in Partners Dashboard
5. **Then** submit for review again when ready

---

## ✅ Quick Fix Summary

**Partners Dashboard** → Your App → **Distribution** → **Withdraw/Cancel** the submission → Change to Development → Install in test store → ✅
