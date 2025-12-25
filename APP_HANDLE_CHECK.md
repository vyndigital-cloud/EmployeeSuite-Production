# ✅ App Handle Configuration

## Your App Details

**App Name:** `Employee Suite`

**App Handle:** `employee-suite-3`

**Application URL:** `https://employeesuite-production.onrender.com`

**Redirect URI:** `https://employeesuite-production.onrender.com/auth/callback`

---

## How to Verify in Shopify Partners Dashboard

1. Go to **Shopify Partners Dashboard** → **Apps** → **Employee Suite**

2. Click **App Setup** (left sidebar)

3. Check these fields:

   **App handle:**
   - Should be: `employee-suite-3`
   - If it's different (like `employee-suite` or `employee-suite-2`), you need to either:
     - Change it in Partners Dashboard to `employee-suite-3`, OR
     - Update `app.json` to match what's in Partners Dashboard

   **Application URL:**
   - Should be: `https://employeesuite-production.onrender.com`

   **Allowed redirection URLs:**
   - Should include: `https://employeesuite-production.onrender.com/auth/callback`

---

## Why the Double Slash Error Happens

The URL `admin.shopify.com/store/employee-suite/apps//auth/callback` shows:
- `apps//` = double slash = missing app handle
- Shopify is trying to construct: `apps/{handle}/auth/callback`
- But the handle is empty, so it becomes `apps//auth/callback`

**Fix:** Make sure the app handle in Partners Dashboard matches `employee-suite-3`

---

## If Handle Doesn't Match

**Option 1: Update Partners Dashboard** (Recommended)
- Change handle in Partners Dashboard to `employee-suite-3`
- Save changes
- Wait 1-2 minutes for propagation

**Option 2: Update app.json**
- Change handle in `app.json` to match Partners Dashboard
- Redeploy to production

---

## After Fixing Handle

1. Uninstall the app from your test store (if installed)
2. Reinstall via OAuth
3. The URL should now work: `admin.shopify.com/store/employee-suite/apps/employee-suite-3/...`

