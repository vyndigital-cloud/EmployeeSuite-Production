# Critical: App Must Be Reinstalled

## The Problem

Even though your redirect URI is correctly configured in Partners Dashboard (`https://employeesuite-production.onrender.com/auth/callback`), you're still seeing the old redirect URI behavior.

## Why This Happens

When you change the redirect URI in Partners Dashboard, **existing app installations continue using the old redirect URI**. Shopify caches the redirect URI when the app is first installed.

## The Solution: Complete Reinstallation

You **MUST** uninstall and reinstall the app:

### Step 1: Uninstall from Store

1. Go to your Shopify store admin: https://admin.shopify.com/store/employee-suite
2. Navigate to: **Apps** (left sidebar)
3. Find: **Employee Suite** in your apps list
4. Click: **Uninstall** or the three dots menu → **Uninstall**
5. Confirm uninstallation

### Step 2: Verify Active Version

1. Go to Partners Dashboard: https://partners.shopify.com
2. Apps → **Employee Suite** → **Versions** (left sidebar)
3. Check which version is **Active** (should have a green checkmark)
4. Make sure the redirect URI is correct on the **Active** version
5. If you need to activate a different version, click "Activate" on the correct one

### Step 3: Reinstall the App

1. In your Shopify store admin, go to: **Apps** → **App and sales channel settings**
2. Click: **Develop apps** (if you're a developer)
3. OR install via Partners Dashboard: Partners Dashboard → Stores → Your Store → Apps tab
4. Find your app and click **Install** or **Test app**

### Step 4: Test OAuth Flow

After reinstalling, try the OAuth flow again. The callback should now go to:
```
https://employeesuite-production.onrender.com/auth/callback?code=...
```

NOT:
```
admin.shopify.com/store/.../apps//auth/callback
```

## Why Reinstallation is Required

- Old installations store the redirect URI in Shopify's system
- Changing it in Partners Dashboard only affects NEW installations
- Existing installations keep using the old redirect URI until reinstalled

## Verification

After reinstalling, check the OAuth callback URL - it should be your app domain, not `admin.shopify.com`.

