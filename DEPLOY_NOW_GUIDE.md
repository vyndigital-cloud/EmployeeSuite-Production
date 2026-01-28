# 🚀 DEPLOY NOW - Quick Guide

## ✅ Pre-Deployment Status

Your app is **READY TO DEPLOY**! Here's what you need to do:

---

## 🔑 Step 1: Generate & Save Secrets

Run this command to generate your secrets:

```bash
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('CRON_SECRET=' + secrets.token_urlsafe(32))"
```

**SAVE THESE VALUES** - You'll need them in Step 3!

---

## 📦 Step 2: Commit & Push Code (Optional)

If you want to commit the diagnostic scripts:

```bash
git add deploy.sh diagnose_orders_inventory_revenue.py fix_orders_inventory_revenue.py
git commit -m "Add deployment and diagnostic tools"
git push origin main
```

**OR** skip this if you don't want to commit diagnostic files.

---

## ⚙️ Step 3: Set Environment Variables in Render

1. Go to: **https://dashboard.render.com**
2. Click on your service (e.g., "employeesuite-production")
3. Click **"Environment"** in the left sidebar
4. Add these variables:

### REQUIRED Variables:

| Variable Name | Value | Where to Get |
|--------------|-------|--------------|
| `SECRET_KEY` | Generated in Step 1 | Your generated secret |
| `CRON_SECRET` | Generated in Step 1 | Your generated secret |
| `SHOPIFY_API_KEY` | From Partners Dashboard | https://partners.shopify.com → Your App → API credentials |
| `SHOPIFY_API_SECRET` | From Partners Dashboard | https://partners.shopify.com → Your App → API credentials |
| `SHOPIFY_REDIRECT_URI` | `https://your-app.onrender.com/oauth/callback` | Replace `your-app` with your actual Render app name |
| `APP_DOMAIN` | `your-app.onrender.com` | Replace `your-app` with your actual Render app name |

### OPTIONAL (but recommended):

| Variable Name | Value |
|--------------|-------|
| `ENVIRONMENT` | `production` |
| `SENTRY_DSN` | Your Sentry DSN (if using Sentry) |

---

## 🚀 Step 4: Deploy

### Option A: Auto-Deploy (if connected to GitHub)
1. Push to GitHub: `git push origin main`
2. Render will automatically deploy
3. Watch the logs in Render dashboard

### Option B: Manual Deploy
1. Go to Render dashboard
2. Click **"Manual Deploy"** → **"Deploy latest commit"**
3. Wait 2-3 minutes for build to complete

---

## ✅ Step 5: Verify Deployment

1. **Check Health Endpoint:**
   ```bash
   curl https://your-app.onrender.com/health
   ```
   Should return: `{"status":"healthy","service":"Employee Suite"...}`

2. **Test the App:**
   - Visit: `https://your-app.onrender.com`
   - Should see the dashboard
   - Try logging in
   - Test connecting a Shopify store

---

## 🐛 Troubleshooting

### Issue: App won't start
- **Check:** Are all REQUIRED environment variables set?
- **Check:** Render logs for error messages
- **Common:** Missing `SECRET_KEY` or `SHOPIFY_API_SECRET`

### Issue: OAuth not working
- **Check:** `SHOPIFY_REDIRECT_URI` matches Partners Dashboard
- **Check:** `SHOPIFY_API_KEY` and `SHOPIFY_API_SECRET` are correct
- **Check:** Redirect URI in Partners Dashboard matches your Render URL

### Issue: Database errors
- **Check:** `DATABASE_URL` is set (Render provides this automatically)
- **Check:** Database is running in Render dashboard

---

## 📋 Quick Checklist

- [ ] Generated SECRET_KEY and CRON_SECRET
- [ ] Set all REQUIRED environment variables in Render
- [ ] Pushed code to GitHub (if auto-deploy) OR manually deployed
- [ ] Verified health endpoint returns 200
- [ ] Tested app login
- [ ] Tested Shopify store connection

---

## 🎉 You're Done!

Your app should now be live at: `https://your-app.onrender.com`

**Next Steps:**
1. Test all features (orders, inventory, revenue)
2. Connect a real Shopify store
3. Monitor Render logs for any errors
4. Set up monitoring (Sentry recommended)

---

## 📞 Need Help?

If something doesn't work:
1. Check Render logs for errors
2. Verify all environment variables are set
3. Test the health endpoint
4. Check browser console for JavaScript errors









