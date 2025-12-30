# 🔧 Fix: "admin.shopify.com refused to connect"

**Issue:** Browser blocking connection/redirect to admin.shopify.com  
**Root Cause:** OAuth redirect happening before App Bridge is fully loaded  
**Status:** ✅ Fixed

---

## 🐛 What Was Wrong

The error "admin.shopify.com refused to connect" was happening because:

1. **OAuth redirect was too fast** - The redirect code was trying to navigate before App Bridge finished loading
2. **App Bridge not ready** - When App Bridge actions weren't available yet, the fallback redirect (`window.top.location.href`) was getting blocked
3. **Race condition** - The script was executing before App Bridge script finished loading

---

## ✅ What I Fixed

### 1. **Wait for App Bridge Script to Load** ✅
- Now waits up to 15 seconds for App Bridge script to load
- Checks if `window['app-bridge']` exists before attempting redirect
- Logs status at each step for debugging

### 2. **Improved Redirect Logic** ✅
- **First:** Try App Bridge `Redirect.Action.REMOTE` (preferred method)
- **Second:** Wait and retry if App Bridge actions not available
- **Fallback:** Use `window.top.location.href` only after App Bridge fails
- **Last resort:** Show manual link if all redirects fail

### 3. **Better Error Handling** ✅
- Prevents double redirects
- Better error messages in console
- Graceful fallback at each step
- Shows manual link if JavaScript fails completely

---

## 🔍 How It Works Now

1. **Page loads** with App Bridge script tag
2. **Wait for script** - Checks every 100ms for App Bridge to load
3. **Once loaded** - Initialize App Bridge app
4. **Use Redirect.Action.REMOTE** - Navigate top-level window to OAuth URL
5. **If App Bridge fails** - Fall back to `window.top.location.href`
6. **If all fails** - Show manual "click here" link

---

## 📋 What to Check

### After Deployment:

1. **Clear browser cache** - Old JavaScript might be cached
2. **Try installing app again** - The OAuth redirect should work smoothly
3. **Check browser console** - Should see:
   ```
   ✅ App Bridge script loaded
   ✅ Using App Bridge Redirect to: [OAuth URL]
   ```

### If Still Getting Error:

1. **Open browser console** (F12 or Cmd+Option+I)
2. **Look for error messages** - The new code logs everything
3. **Check Network tab** - See if App Bridge script is loading
4. **Verify CSP headers** - Make sure `admin.shopify.com` is in `connect-src`

---

## 🔧 Technical Details

### Before (Problematic):
```javascript
// Tried to redirect immediately - App Bridge might not be loaded
var AppBridge = window['app-bridge'];
if (AppBridge) {
    // Use App Bridge
} else {
    // Immediate fallback - gets blocked
    window.top.location.href = url;
}
```

### After (Fixed):
```javascript
// Wait for App Bridge script to load first
function checkScriptLoaded() {
    if (window['app-bridge']) {
        scriptLoaded = true;
        tryRedirect(); // Now App Bridge is ready
    } else {
        setTimeout(checkScriptLoaded, 100); // Wait and retry
    }
}
```

---

## 🎯 Expected Behavior

**Before Fix:**
- ❌ "admin.shopify.com refused to connect" error
- ❌ Redirect fails or gets blocked

**After Fix:**
- ✅ App Bridge loads completely
- ✅ Redirect uses App Bridge Redirect.Action.REMOTE
- ✅ Smooth redirect to OAuth page
- ✅ No connection refused errors

---

## 🚨 If Issues Persist

If you still see "refused to connect" after deployment:

1. **Check CSP headers** - Verify `admin.shopify.com` is in `connect-src`
2. **Check browser console** - Look for the new detailed error messages
3. **Try incognito mode** - Rule out browser extensions/cache
4. **Check Network tab** - Verify App Bridge CDN is accessible
5. **Verify environment** - Make sure `SHOPIFY_API_KEY` is set correctly

---

**Status:** ✅ Deployed and ready to test





