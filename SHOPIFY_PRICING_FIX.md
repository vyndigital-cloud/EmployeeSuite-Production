# 🔧 Shopify Pricing Details - Fix Error

## ❌ Current Error

**Error Message:** "Enter a valid URL format, e.g. https://example.com/billing-info"

**Location:** Pricing details → "I have approval to charge merchants outside of the Shopify Billing API"

**Issue:** The checkbox is checked and the URL field has a placeholder URL (`https://example.com/billing-info`)

---

## ✅ Solution

### Option 1: Uncheck the Box (Recommended)

Since you're using **Stripe** for billing (not charging outside Shopify Billing API), you should:

1. **Uncheck** the checkbox: "I have approval to charge merchants outside of the Shopify Billing API"
2. The URL field will disappear
3. Error will be resolved ✅

**Why:** Your app uses Stripe, which is integrated through your app's billing system, not a separate external service.

---

### Option 2: If You Need External Billing (Not Recommended)

If for some reason you DO need external billing approval:

1. **Keep checkbox checked**
2. **Replace the placeholder URL** with a valid URL, such as:
   ```
   https://employeesuite-production.onrender.com/billing
   ```
   OR
   ```
   https://employeesuite-production.onrender.com/subscribe
   ```

**Note:** This is only needed if you're charging merchants through a service OUTSIDE of Shopify's billing system. Since you're using Stripe through your app, you don't need this.

---

## 🎯 Recommended Action

**Uncheck the box** - This is the correct setting for your app since you're using Stripe for billing, not an external billing service outside of Shopify's system.

---

## 📋 Other Pricing Details to Check

While you're in the Pricing section:

1. **Display name:** "Standard Plan" (13/18 characters) ✅
2. **Top features:** Currently 0 features - you can add up to 8 optional features describing your plan
3. **Pricing URL (optional):** Currently has placeholder - you can leave blank or add:
   ```
   https://employeesuite-production.onrender.com/subscribe
   ```

---

## ✅ After Fixing

1. Click **"Save"** at the top
2. The red error should disappear
3. You can proceed with app submission












