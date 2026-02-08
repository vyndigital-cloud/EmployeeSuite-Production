# 🛑 IFRAME SESSION DEPLOYMENT - VERIFICATION

## Deployment Details
**Status:** ✅ PUSHED TO PRODUCTION (8b621cd)
**Time:** 2026-02-08 08:35:00 AWST
**Fix:** App Bridge Breakout + Session Debugging

## 🔍 How to Verify the Fix

### 1. Embedded App Redirection (The "Settings" Test)
1. Open Shopify Admin -> Apps -> Employee Suite
2. Click on "Settings"
3. **EXPECTED BEHAVIOR:**
   - The iframe should display a brief "Redirecting..." message
   - The parent window (Shopify Admin) might briefly show a loading bar
   - You should land on the Settings page **WITHOUT** being redirected to /login
   - You should stay logged in even after multiple clicks

### 2. Session Debugging Logs
Check your application logs for:
```
🔍 SESSION DEBUG [shopify_settings - START]:
  - Is Embedded: True
  - Session Cookie Present: True
  - User ID: 11
```
If you see `User ID: NO_USER` but `Session Cookie Present: True`, the fix is still deploying or browser needs a refresh.

### 3. Cookie Policy Verification
In Chrome/Edge DevTools -> Application -> Cookies:
- Find your app's domain
- Verify `session` cookie has:
  - `SameSite=None`
  - `Secure=True`
  - `Partitioned` (optional but good)

## 🚨 Troubleshooting

If redirects still loop:
1. **Clear Site Data:** DevTools -> Application -> Storage -> Clear site data
2. **Hard Refresh:** Command+Shift+R
3. **Check Console:** Look for "App Bridge redirect initiated" messages

## Rollback Command
If critical issues occur:
```bash
git revert HEAD
git push origin main
```
