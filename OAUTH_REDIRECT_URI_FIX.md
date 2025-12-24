# 🔧 Fix OAuth Redirect URI Error

## Error Message
```
invalid_request: The redirect_uri is not whitelisted
```

## What This Means
Shopify is rejecting the OAuth request because the `redirect_uri` parameter doesn't match any of the URLs configured in your Shopify Partners Dashboard.

---

## ✅ Quick Fix Steps

### Step 1: Verify Redirect URI in Code
The code uses this redirect URI:
```
https://employeesuite-production.onrender.com/auth/callback
```

**Check your environment variable:**
- In Render Dashboard → Your Service → Environment
- Look for `SHOPIFY_REDIRECT_URI`
- If it's set, it must be: `https://employeesuite-production.onrender.com/auth/callback`
- If it's missing or different, either:
  - Set it to: `https://employeesuite-production.onrender.com/auth/callback`
  - Or delete it (code will use the default)

---

### Step 2: Add Redirect URI to Partners Dashboard

**Go to Shopify Partners Dashboard:**
1. Navigate to: https://partners.shopify.com
2. Click **Apps** → Select your app
3. Click **App Setup** (left sidebar)
4. Scroll to **"Allowed redirection URLs"** section
5. Click **"Add URL"** or **"Add redirection URL"**

**Add this EXACT URL:**
```
https://employeesuite-production.onrender.com/auth/callback
```

**Critical Requirements:**
- ✅ Must use `https://` (not `http://`)
- ✅ No trailing slash at the end
- ✅ Exact domain: `employeesuite-production.onrender.com`
- ✅ Exact path: `/auth/callback`
- ✅ No query parameters
- ✅ Case-sensitive (use lowercase)

---

### Step 3: Verify App Configuration

**In Partners Dashboard → App Setup, also check:**

1. **App URL:**
   - Should be: `https://employeesuite-production.onrender.com`
   - No trailing slash

2. **App Status:**
   - Should be **Development** or **Unlisted** (for testing)
   - If it's **Public**, you can't test install it the same way

3. **API Key:**
   - Must match your `SHOPIFY_API_KEY` environment variable
   - Check in Render Dashboard → Environment

---

### Step 4: Wait for Propagation

After adding the redirect URI:
1. **Save** the changes in Partners Dashboard
2. **Wait 1-2 minutes** for changes to propagate
3. Try installing again

---

## 🔍 Troubleshooting

### Issue: Redirect URI still not working after adding

**Check these:**

1. **Multiple redirect URIs:**
   - Make sure you didn't add a duplicate with a trailing slash
   - Remove any incorrect versions
   - Keep only: `https://employeesuite-production.onrender.com/auth/callback`

2. **Environment variable mismatch:**
   - Check Render Dashboard → Environment → `SHOPIFY_REDIRECT_URI`
   - If set, it must match exactly what's in Partners Dashboard
   - Consider removing it to use the code default

3. **Domain mismatch:**
   - If your app is deployed to a different domain, update both:
     - Partners Dashboard redirect URI
     - Environment variable `SHOPIFY_REDIRECT_URI`

4. **Check logs:**
   - In Render Dashboard → Logs
   - Look for: `OAuth install: Using redirect_uri=...`
   - Verify it matches what's in Partners Dashboard

---

### Issue: Different domain

If your app is on a different domain (not `employeesuite-production.onrender.com`):

1. **Update code default** in `shopify_oauth.py`:
   ```python
   REDIRECT_URI = os.getenv('SHOPIFY_REDIRECT_URI', 'https://YOUR-ACTUAL-DOMAIN.com/auth/callback')
   ```

2. **Set environment variable** in Render:
   ```
   SHOPIFY_REDIRECT_URI=https://YOUR-ACTUAL-DOMAIN.com/auth/callback
   ```

3. **Add to Partners Dashboard:**
   ```
   https://YOUR-ACTUAL-DOMAIN.com/auth/callback
   ```

---

## ✅ Verification Checklist

- [ ] Redirect URI added to Partners Dashboard: `https://employeesuite-production.onrender.com/auth/callback`
- [ ] No trailing slash in redirect URI
- [ ] Using `https://` (not `http://`)
- [ ] Environment variable `SHOPIFY_REDIRECT_URI` matches (or is unset to use default)
- [ ] App URL in Partners Dashboard matches your domain
- [ ] App status is Development or Unlisted
- [ ] Waited 1-2 minutes after saving
- [ ] Checked logs to verify redirect URI being used

---

## 🎯 Most Common Cause

**99% of the time**, this error happens because:
1. The redirect URI is missing from Partners Dashboard
2. There's a typo or mismatch (trailing slash, wrong domain, etc.)
3. The environment variable is set to a different value

**Quick fix:** Add the exact URL to Partners Dashboard and wait 1-2 minutes.

---

## 📝 Code Changes Made

The code has been updated to:
1. ✅ Properly URL-encode the redirect_uri in the OAuth query string
2. ✅ Add logging to show which redirect_uri is being used
3. ✅ Ensure exact match with Partners Dashboard configuration

---

## Need More Help?

If the issue persists after following these steps:
1. Check Render logs for the exact redirect_uri being used
2. Compare it character-by-character with Partners Dashboard
3. Verify your app's API key matches in both places
4. Try removing the `SHOPIFY_REDIRECT_URI` environment variable to use the code default

