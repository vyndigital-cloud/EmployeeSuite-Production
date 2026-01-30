# ✅ CONFIRMED: Redirect URI MUST Be This

## Your Code Uses:

```python
REDIRECT_URI = os.getenv('SHOPIFY_REDIRECT_URI', 'https://employeesuite-production.onrender.com/auth/callback')
```

From `shopify_oauth.py` line 24.

## ✅ CORRECT Redirect URI:

```
https://employeesuite-production.onrender.com/auth/callback
```

**This IS correct and MUST match exactly in Partners Dashboard.**

## Why It Must Match Exactly

Shopify validates that the redirect URI in the OAuth request matches EXACTLY what's configured in Partners Dashboard. If there's any difference (even a trailing slash), OAuth will fail.

## What You Should See In Partners Dashboard

In the "Redirect URLs" field, you should see:
```
https://employeesuite-production.onrender.com/auth/callback
```

**NOT:**
- ❌ `/auth/callback` (missing domain)
- ❌ `http://employeesuite-production.onrender.com/auth/callback` (wrong protocol)
- ❌ `https://employeesuite-production.onrender.com/auth/callback/` (trailing slash)
- ❌ `https://employeesuite-production.onrender.com/auth/callBack` (wrong case)

## If You're Seeing Something Different

If Partners Dashboard shows a different redirect URI, that's why OAuth is failing. You need to:

1. Edit the active version
2. Change redirect URI to: `https://employeesuite-production.onrender.com/auth/callback`
3. Save
4. Uninstall and reinstall the app










