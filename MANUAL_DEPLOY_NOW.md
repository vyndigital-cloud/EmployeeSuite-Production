# 🚀 Manual Deploy on Render - Do This Now

## Quick Steps (2 minutes)

### Step 1: Go to Render Dashboard
1. Open: **https://dashboard.render.com**
2. Sign in if needed
3. Click on your app/service (probably called "employeesuite-production" or similar)

### Step 2: Manual Deploy
1. In the top right, click **"Manual Deploy"** dropdown
2. Select **"Deploy latest commit"**
3. Wait 2-5 minutes for build to complete

### Step 3: Check Logs
1. Click **"Logs"** tab (left sidebar)
2. Watch for:
   - ✅ "Building..." 
   - ✅ "Installing dependencies..."
   - ✅ "Starting service..."
   - ✅ "Listening at: http://0.0.0.0:10000"

---

## If "Manual Deploy" Button is Grayed Out

### Option A: Check Branch Settings
1. Go to **Settings** → **Build & Deploy**
2. Make sure **Branch** is set to `main`
3. Make sure **Auto-Deploy** is enabled (should be "Yes")
4. Try manual deploy again

### Option B: Trigger via GitHub
If Render still won't deploy, create a dummy commit:

```bash
git commit --allow-empty -m "Trigger Render deployment"
git push origin main
```

This empty commit will trigger auto-deploy.

---

## Verify Deployment Worked

### Check 1: Health Endpoint
Visit: https://employeesuite-production.onrender.com/health

Should return:
```json
{
  "status": "healthy",
  "service": "Employee Suite",
  "version": "2.0"
}
```

### Check 2: Recent Deploy
In Render dashboard → **Events** tab:
- Should see recent deploy with commit hash: `d41a618`
- Status should be "Live" (green)

---

## If Still Not Working

1. **Check Render Logs** for errors
2. **Check GitHub** - make sure commit `d41a618` is on `main` branch
3. **Try redeploying** - sometimes Render just needs a nudge

---

## The Fix That Was Deployed

This deployment includes:
- ✅ **CSP frame-ancestors fix** - Includes specific shop domain
- ✅ **Better embedded app loading** - Should fix blank iframe issues
- ✅ **Improved browser compatibility** - Works better in Safari/Chrome/Firefox

After deployment, test your embedded app in Shopify admin - it should load properly now!

