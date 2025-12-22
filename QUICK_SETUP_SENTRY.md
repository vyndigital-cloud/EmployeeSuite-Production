# 🚀 Quick Setup: Sentry Error Monitoring

**5-Minute Setup Guide**

---

## Step 1: Create Sentry Account (2 minutes)

1. Go to **https://sentry.io/signup/**
2. Sign up with email or GitHub
3. Choose **"Start with the Developer plan"** (Free tier - 5,000 events/month)
4. Click **"Create Project"**
5. Select **"Flask"** as your platform
6. Project name: `Employee Suite` (or your choice)
7. Click **"Create Project"**

---

## Step 2: Get Your DSN (30 seconds)

After creating the project, Sentry will show you a page with code examples.

**Look for the DSN** - it looks like this:
```
https://abc123def456@o123456.ingest.sentry.io/789012
```

**Copy this DSN** - you'll need it in the next step.

---

## Step 3: Add to Render (1 minute)

1. Go to your **Render Dashboard**
2. Select your **Employee Suite** service
3. Go to **Environment** tab
4. Click **"Add Environment Variable"**
5. Add these variables:

```
Key: SENTRY_DSN
Value: https://your-key@sentry.io/your-project-id
```

(Optional but recommended):
```
Key: ENVIRONMENT
Value: production

Key: RELEASE_VERSION
Value: 1.0.0
```

6. Click **"Save Changes"**

---

## Step 4: Redeploy (1 minute)

**Option A: Auto-Deploy (if enabled)**
- Render will automatically redeploy when you save environment variables
- Wait 2-3 minutes for deployment to complete

**Option B: Manual Redeploy**
1. In Render Dashboard → Your Service
2. Click **"Manual Deploy"** → **"Deploy latest commit"**
3. Wait for deployment to complete

---

## Step 5: Verify It's Working (30 seconds)

1. **Check Render Logs:**
   - Look for: `"Sentry error monitoring initialized"`
   - If you see: `"SENTRY_DSN not set"` → Environment variable not set correctly

2. **Test Sentry (Optional):**
   - Visit: `https://your-app.onrender.com/test-sentry` (if you add test route)
   - Or just wait for a real error to occur
   - Check Sentry dashboard - errors appear within seconds

---

## ✅ That's It!

Sentry is now active and will:
- ✅ Capture all errors automatically
- ✅ Send you email alerts
- ✅ Show detailed stack traces
- ✅ Track performance metrics

---

## 🎯 Quick Checklist

- [ ] Sentry account created
- [ ] Project created (Flask platform)
- [ ] DSN copied
- [ ] `SENTRY_DSN` added to Render environment variables
- [ ] App redeployed
- [ ] Logs show "Sentry error monitoring initialized"

---

## 💡 Pro Tips

1. **Set up Email Alerts:**
   - Sentry Dashboard → Settings → Alerts
   - Add your email for instant notifications

2. **Slack Integration (Optional):**
   - Sentry Dashboard → Settings → Integrations
   - Connect Slack for team notifications

3. **Free Tier Limits:**
   - 5,000 events/month (plenty for starting)
   - Upgrade to Team plan ($26/mo) when you need more

---

**Need Help?** Check `PRODUCTION_SETUP.md` for detailed troubleshooting.




