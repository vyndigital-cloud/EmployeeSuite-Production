# ✅ ACTIVATE THE VERSION - This Will Fix It

## What I See In Your Screenshot

You're on the "Create a version" page, and the redirect URI is correctly set to:
```
https://employeesuite-production.onrender.com/auth/callback
```

**BUT** - The problem is likely that the **ACTIVE version** (the one actually being used) has a different redirect URI.

## 🔴 CRITICAL STEPS (Do These Now)

### Step 1: Save This Version First

On the page you're currently viewing:
1. Scroll to the bottom
2. Click **"Save version"** or **"Create version"** button
3. Wait for it to save

### Step 2: Activate This Version

1. After saving, you should see a list of versions
2. Find the version you just created
3. Look for an **"Activate"** or **"Set as active"** button
4. Click it to make this version active

**OR** if you're still on the creation page:
- After clicking "Save version", it should ask if you want to activate it
- Click **"Yes"** or **"Activate"**

### Step 3: Verify The Active Version

1. Go to: Partners Dashboard → Apps → Employee Suite → **Versions** (left sidebar)
2. Look for which version has the **green checkmark** ✓ or says **"Active"**
3. Click on that active version
4. Scroll to **"Redirect URLs"** section
5. **What does it show?**
   - Should be: `https://employeesuite-production.onrender.com/auth/callback`
   - If it shows something different (like `/auth/callback` or nothing), that's the problem

### Step 4: If Active Version Has Wrong Redirect URI

1. Click **"Edit"** on the active version
2. Change the Redirect URL to: `https://employeesuite-production.onrender.com/auth/callback`
3. Click **"Save"**
4. Make sure it's still **Active**

### Step 5: Uninstall and Reinstall App

After verifying the active version has the correct redirect URI:

1. Go to your Shopify store admin: `https://admin.shopify.com/store/employee-suite`
2. Go to **Apps** (left sidebar)
3. Find "Employee Suite"
4. Click **Uninstall** → Confirm
5. Wait 30 seconds
6. Go back to Partners Dashboard → Stores → employee-suite → Apps tab
7. Click **Install** or **Test app**
8. Test again

## 📋 Quick Checklist

- [ ] Saved the new version with correct redirect URI
- [ ] Activated the new version (or verified existing active version has correct URI)
- [ ] Verified active version shows: `https://employeesuite-production.onrender.com/auth/callback`
- [ ] Uninstalled app from store
- [ ] Reinstalled app
- [ ] Tested OAuth flow again

## Why This Matters

Shopify uses the redirect URI from the **ACTIVE version**, not from versions you're creating. If the active version has the wrong URI (or a relative path), OAuth will fail.

The redirect URI MUST be the full URL: `https://employeesuite-production.onrender.com/auth/callback`

## Also Note

I see your Webhooks API Version is set to "2025-10" but your `app.json` uses "2024-10". This won't cause the redirect issue, but you may want to align them later. For now, focus on the redirect URI fix.

