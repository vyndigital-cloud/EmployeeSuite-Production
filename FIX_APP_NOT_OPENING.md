# Fix: App Not Opening When Clicked

## Problem
App is installed, but clicking it in Shopify admin just stays on the Apps page. Doesn't open the app.

## Why This Happens
Shopify doesn't know what URL to load when the app is clicked. The "App URL" in Partners Dashboard is missing or wrong.

## Fix

### Go to Partners Dashboard
1. https://partners.shopify.com
2. Click your app: **Employee Suite**
3. Click **App Setup** in the left sidebar

### Set App URL
Scroll to **App URL** section and set:
```
https://employeesuite-production.onrender.com
```

**Make sure:**
- No trailing slash
- `https://` not `http://`
- Exact domain: `employeesuite-production.onrender.com`

### Also Check
In the same App Setup page, verify:

**Allowed redirection URL(s):**
```
https://employeesuite-production.onrender.com/auth/callback
```

**Embedded in Shopify admin:**
- Should be checked/enabled

### Save
Click **Save** at the bottom of the page.

---

## After Fixing

1. Wait 1-2 minutes for changes to sync
2. Go back to your store: https://admin.shopify.com/store/employee-suite
3. Click **Apps** → **Employee Suite**
4. Should now open the app

---

## What Should Happen
When you click the app, it should:
- Load in an embedded iframe inside Shopify admin
- Show your dashboard
- URL should be something like: `https://admin.shopify.com/store/employee-suite/apps/employee-suite`

If it's still not working after this, the app might need to be reinstalled.

