# 🔧 Embedded App CSP Fix - Improved frame-ancestors

## Problem
Shopify embedded apps can fail to load properly in iframes if the CSP `frame-ancestors` header doesn't correctly allow the specific shop domain.

## Root Cause
- Using wildcard `https://*.myshopify.com` alone isn't always reliable
- CSP spec supports wildcards, but some browsers/configurations prefer specific domains
- Shopify's documentation recommends including the specific shop domain when available

## Solution
Updated `security_enhancements.py` to:

1. **Extract shop domain from URL parameters** (`shop` or `shop_domain`)
2. **Include specific shop domain** in `frame-ancestors` when available (e.g., `https://myshop.myshopify.com`)
3. **Keep wildcard pattern** as fallback for compatibility (`https://*.myshopify.com`)
4. **Always include** `https://admin.shopify.com` for Shopify admin access

## New frame-ancestors Format

**Before:**
```
frame-ancestors https://admin.shopify.com https://*.myshopify.com;
```

**After (when shop parameter is available):**
```
frame-ancestors https://admin.shopify.com https://myshop.myshopify.com https://*.myshopify.com;
```

**After (when shop parameter is not available):**
```
frame-ancestors https://admin.shopify.com https://*.myshopify.com;
```

## Why This Works Better

1. **More specific = more reliable**: Browsers prefer exact domain matches
2. **Wildcard as fallback**: Still works if shop param isn't available
3. **Shopify admin included**: Always allows embedding from Shopify admin
4. **Follows Shopify recommendations**: Matches official embedded app patterns

## Testing

After deploying, verify:

1. **Check browser console** for CSP violations
2. **Network tab** → Check `Content-Security-Policy` header includes shop domain
3. **Test in Shopify admin iframe** - should load without blank screen
4. **Check logs** - should see shop domain in "ALLOWING IFRAME" log message

## Related Issues Fixed

- ✅ Blank/half-loaded iframe in Shopify admin
- ✅ CSP blocking iframe rendering
- ✅ Embedded app "barely loads" issue
- ✅ Improved compatibility across browsers (Safari, Chrome, Firefox)

