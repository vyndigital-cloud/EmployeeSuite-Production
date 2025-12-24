# App Bridge Loading Issue

## Status: Investigating

The console shows "App Bridge not available after timeout" which means App Bridge script is loading but `window['app-bridge']` is not becoming available.

---

## Possible Causes

1. **Script loading but not executing** - The script tag loads but the global object isn't set
2. **CSP blocking execution** - Content Security Policy might be preventing script execution
3. **Timing issue** - Script needs more time to initialize (currently 2 seconds timeout)
4. **Browser extension interference** - MetaMask or other extensions might interfere

---

## Current CSP Settings

```python
"script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.shopify.com https://js.stripe.com https://www.googletagmanager.com; "
```

This should allow App Bridge to load from `https://cdn.shopify.com/shopifycloud/app-bridge.js`.

---

## Non-Critical Errors (Can Ignore)

- **MetaMask errors**: Browser extension trying to inject code - harmless
- **App Bridge CSS failed to load**: CSS is non-critical, App Bridge JS is what matters

---

## Next Steps

1. Verify CSP allows script execution from `cdn.shopify.com`
2. Check if script is actually loading (Network tab)
3. Increase timeout if script is slow to initialize
4. Check browser console for any CSP violation errors

---

## Form-Action CSP Fix

The form-action CSP has been fixed to explicitly allow:
```
form-action 'self' https://employeesuite-production.onrender.com;
```

This should allow form submissions to `/install` endpoint.

