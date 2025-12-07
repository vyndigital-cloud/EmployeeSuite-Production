# 💰 How Shopify Billing Works & Where Your Money Goes

**Complete guide to Shopify App Store billing**

---

## 🎯 Two Billing Systems

Your app has **TWO billing systems**:

1. **Stripe Billing** - For direct customers (standalone website)
2. **Shopify Billing API** - For App Store customers (Shopify App Store)

---

## 🛍️ Shopify Billing (App Store)

### How It Works

When a user installs your app from the **Shopify App Store**:

1. **User Installs App:**
   - User clicks "Install" in Shopify App Store
   - OAuth flow completes
   - App is installed in their Shopify store

2. **Subscription Created:**
   ```python
   # Your app creates a recurring charge
   billing.create_recurring_charge(
       name="Employee Suite Pro",
       price=500.00,  # $500/month
       trial_days=2
   )
   ```

3. **User Approves Payment:**
   - Shopify shows a confirmation page
   - User clicks "Approve" to subscribe
   - Payment is authorized

4. **Money Goes to Your Shopify Partner Account:**
   - **NOT directly to your bank**
   - Goes to your **Shopify Partner account**
   - You get paid monthly (Shopify's payout schedule)

---

## 💳 Where Does the Money Go?

### Payment Flow:

```
Customer Pays $500/month
    ↓
Shopify Collects Payment
    ↓
Shopify Holds in Partner Account
    ↓
Shopify Pays You (Monthly Payout)
    ↓
Money Goes to Your Bank Account
```

### Shopify Partner Payouts:

1. **Payout Schedule:**
   - Shopify pays you **monthly**
   - Usually around the **15th of each month**
   - For the previous month's revenue

2. **Where to See Your Money:**
   - **Shopify Partner Dashboard** → **Payouts**
   - Shows pending and completed payouts
   - Shows breakdown by app/charge

3. **Payout Method:**
   - You set up in Partner Dashboard
   - Can be: Bank account, PayPal, etc.
   - Configure in: Partner Dashboard → Settings → Payouts

---

## 📊 How Shopify Billing Works

### Step-by-Step Process:

1. **App Installation:**
   ```
   User installs app → OAuth completes → App installed
   ```

2. **Create Charge:**
   ```python
   # Your app calls Shopify API
   POST /admin/api/2024-10/recurring_application_charges.json
   {
     "recurring_application_charge": {
       "name": "Employee Suite Pro",
       "price": 500.00,
       "trial_days": 2
     }
   }
   ```

3. **Shopify Returns:**
   ```json
   {
     "recurring_application_charge": {
       "id": 123456,
       "confirmation_url": "https://shop.myshopify.com/admin/charges/...",
       "status": "pending"
     }
   }
   ```

4. **User Approves:**
   - User visits `confirmation_url`
   - Clicks "Approve" in Shopify admin
   - Status changes to "active"

5. **Payment Processed:**
   - Shopify charges customer's payment method
   - Money goes to your Partner account
   - Webhook notifies your app: `app_subscriptions/update`

---

## 💰 Payment Details

### What You Charge:

- **Setup Fee:** $1,000 (one-time) - via usage charge
- **Monthly Fee:** $500/month (recurring) - via recurring charge
- **Trial:** 2 days free

### Where Money Goes:

1. **Immediate:** Shopify Partner account (pending)
2. **Monthly:** Shopify pays you (around 15th of month)
3. **Final:** Your bank account (via payout method)

---

## 🔍 Tracking Your Revenue

### Shopify Partner Dashboard:

1. **Go to:** https://partners.shopify.com
2. **Navigate to:** Your App → Analytics
3. **See:**
   - Total revenue
   - Active subscriptions
   - Pending payouts
   - Payment history

### In Your App:

- `charge_id` stored in database
- Webhook updates subscription status
- You can track active subscriptions

---

## ⚖️ Shopify Billing vs Stripe Billing

### Shopify Billing (App Store):
- ✅ **Where:** Shopify Partner account
- ✅ **Payout:** Monthly (around 15th)
- ✅ **Fees:** Shopify takes a cut (usually 0% for first $1M, then 15%)
- ✅ **Use:** For App Store customers
- ✅ **Payment:** Handled by Shopify

### Stripe Billing (Direct):
- ✅ **Where:** Stripe account → Your bank
- ✅ **Payout:** Daily/weekly (configurable)
- ✅ **Fees:** Stripe takes 2.9% + $0.30 per transaction
- ✅ **Use:** For direct website customers
- ✅ **Payment:** Handled by Stripe

---

## 📋 Setup Required

### To Receive Payments:

1. **Shopify Partner Account:**
   - ✅ You already have this (to create the app)
   - Need to verify payout method

2. **Set Up Payout Method:**
   - Go to Partner Dashboard → Settings → Payouts
   - Add bank account or PayPal
   - Verify your identity (if required)

3. **Tax Information:**
   - Shopify may require tax forms
   - Fill out W-9 (US) or equivalent
   - Required before first payout

---

## 💡 Important Notes

### Shopify's Cut:

- **First $1M revenue:** 0% (you keep 100%)
- **After $1M:** 15% (you keep 85%)
- **This is for App Store apps only**

### Payout Timeline:

- **Customer pays:** Immediately when they approve
- **You see it:** In Partner Dashboard (pending)
- **You get paid:** Around 15th of next month
- **Example:** Customer pays Jan 1 → You get paid Feb 15

### Charge Status:

- **Pending:** User hasn't approved yet
- **Active:** User approved, payment processing
- **Declined:** Payment failed
- **Cancelled:** User cancelled subscription

---

## 🔔 Webhook Notifications

Your app receives webhooks when:

1. **Subscription Created:**
   - `app_subscriptions/update` webhook
   - Status: "pending" → "active"

2. **Payment Processed:**
   - `app_subscriptions/update` webhook
   - Status: "active"

3. **Payment Failed:**
   - `app_subscriptions/update` webhook
   - Status: "declined"

4. **Subscription Cancelled:**
   - `app_subscriptions/update` webhook
   - Status: "cancelled"

---

## ✅ Summary

**How it works:**
1. User installs app from App Store
2. Your app creates subscription charge
3. User approves in Shopify admin
4. Shopify charges customer
5. Money goes to your Partner account
6. Shopify pays you monthly (around 15th)

**Where money goes:**
- Customer → Shopify → Your Partner Account → Your Bank (monthly)

**To get paid:**
- Set up payout method in Partner Dashboard
- Fill out tax forms if required
- Wait for monthly payout (around 15th)

**You keep:**
- 100% of first $1M revenue
- 85% after $1M (Shopify takes 15%)

---

**Last Updated:** January 6, 2025

