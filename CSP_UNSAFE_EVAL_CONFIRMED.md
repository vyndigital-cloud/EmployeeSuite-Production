# CSP unsafe-eval Status

## ✅ Status: Already Configured

Both CSP configurations (embedded and non-embedded) already include `'unsafe-eval'`:

**Embedded CSP:**
```python
"script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.shopify.com ..."
```

**Non-Embedded CSP:**
```python
"script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com ..."
```

---

## Verification

The deployed CSP header confirms `unsafe-eval` is present:
```
script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com https://js.stripe.com
```

---

## If You Still See the Error

If the browser still shows CSP errors about `unsafe-eval`:

1. **Clear browser cache** - Old CSP headers might be cached
   - Chrome: Ctrl+Shift+Delete (Windows/Linux) or Cmd+Shift+Delete (Mac)
   - Select "Cached images and files"
   - Clear data

2. **Hard refresh the page**
   - Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)

3. **Check Developer Tools**
   - Open Network tab
   - Find the page request
   - Check the `Content-Security-Policy` response header
   - Verify it includes `'unsafe-eval'`

4. **Check if it's a report-only CSP**
   - Look for `Content-Security-Policy-Report-Only` header
   - This header doesn't block, only reports

5. **Check for meta tag CSP**
   - View page source
   - Search for `<meta http-equiv="Content-Security-Policy"`
   - Meta tags can override HTTP headers

---

## Why unsafe-eval is Needed

Third-party libraries may require `unsafe-eval`:
- **App Bridge** (Shopify) - May use dynamic code evaluation
- **Stripe.js** - May use eval for some features
- **Google Analytics/Tag Manager** - Uses eval for tracking scripts

This is acceptable because:
- You trust these third-party libraries
- Other CSP directives still protect against XSS
- This is standard for embedded Shopify apps

---

## Current Configuration

✅ Embedded: `'unsafe-eval'` included  
✅ Non-Embedded: `'unsafe-eval'` included  
✅ Deployed: Confirmed in production headers

If errors persist after clearing cache, it may be a browser extension or other source.

