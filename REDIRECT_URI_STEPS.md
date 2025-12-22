# ✅ Add Redirect URI - Exact Steps

## Where to Add It

**Shopify Partners Dashboard** → Your App → **App Setup** → Scroll to **"Allowed redirection URLs"**

---

## Exact URL to Add

Copy and paste this EXACT URL:

```
https://employeesuite-production.onrender.com/auth/callback
```

**Important:**
- ✅ Use `https://` (not `http://`)
- ✅ No trailing slash at the end
- ✅ Exact domain: `employeesuite-production.onrender.com`
- ✅ Exact path: `/auth/callback`

---

## Steps

1. Go to **Shopify Partners Dashboard**
2. Click **Apps** → **Employee Suite**
3. Click **App Setup** (left sidebar)
4. Scroll down to **"Allowed redirection URLs"** section
5. Click **"Add URL"** or **"Add redirection URL"**
6. Paste: `https://employeesuite-production.onrender.com/auth/callback`
7. Click **Save** or **Add**

---

## ✅ Verify It Was Added

You should see the URL in the list:
- `https://employeesuite-production.onrender.com/auth/callback`

If it's already there, you're good! ✅

---

## After Adding Redirect URI

1. Wait 1-2 minutes for changes to propagate
2. Change app status to **Development** (see `APP_UNDER_REVIEW_FIX.md`)
3. Try installing in test store again

---

## Why This Matters

The redirect URI must match EXACTLY what your code uses. Your code uses:
```python
REDIRECT_URI = 'https://employeesuite-production.onrender.com/auth/callback'
```

So that's what needs to be in Partners Dashboard! ✅
