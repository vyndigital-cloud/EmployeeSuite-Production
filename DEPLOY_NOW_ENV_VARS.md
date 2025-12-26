# 🚀 DEPLOYMENT - Environment Variables Setup

## ✅ Code is Pushed to GitHub!

Your code has been pushed to: `https://github.com/vyndigital-cloud/EmployeeSuite-Production.git`

---

## 🔐 CRITICAL: Set Environment Variables in Render

**Your app will FAIL without these!** Set them in Render Dashboard:

### Step 1: Go to Render Dashboard
1. Visit: https://dashboard.render.com
2. Find your **EmployeeSuite-Production** service
3. Click on it → Go to **"Environment"** tab

### Step 2: Add These Variables

#### **Shopify Credentials (REQUIRED - Just Fixed!)**
```
SHOPIFY_API_KEY=<your-api-key-from-partners-dashboard>
SHOPIFY_API_SECRET=<your-api-secret-from-partners-dashboard>
SHOPIFY_REDIRECT_URI=https://employeesuite-production.onrender.com/auth/callback
```

#### **Security (REQUIRED)**
```
SECRET_KEY=<generate-a-random-32-char-string>
CRON_SECRET=<generate-a-random-32-char-string>
```

**To generate secrets, run:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```
Run it twice to get two different secrets.

#### **Database (Auto-provided by Render)**
```
DATABASE_URL=<Render provides this automatically>
```

#### **Optional but Recommended**
```
ENVIRONMENT=production
FLASK_ENV=production
```

---

## 🚀 Deploy Now

### Option 1: Auto-Deploy (If Enabled)
- Render will automatically deploy when you push to GitHub
- Check the "Events" tab to see deployment status
- Wait 2-3 minutes for build to complete

### Option 2: Manual Deploy
1. Go to Render Dashboard → Your Service
2. Click **"Manual Deploy"** → **"Deploy latest commit"**
3. Wait for build to complete

---

## ✅ Verify Deployment

After deployment completes:

1. **Check Health:**
   ```
   https://employeesuite-production.onrender.com/health
   ```
   Should return: `{"status": "healthy"}`

2. **Test Shopify Connection:**
   ```
   https://employeesuite-production.onrender.com/settings/shopify
   ```
   Should show connection form (NOT "Configuration Error")

3. **Check Logs:**
   - Go to Render Dashboard → Your Service → "Logs"
   - Should NOT see: "SHOPIFY_API_KEY environment variable is not set!"

---

## 🎯 Quick Checklist

- [ ] Code pushed to GitHub ✅ (DONE)
- [ ] Environment variables set in Render
- [ ] Deployment triggered
- [ ] Health check passes
- [ ] Shopify settings page loads without errors

---

## 🐛 If Deployment Fails

1. **Check Render Logs:**
   - Look for error messages
   - Common issues: Missing env vars, import errors

2. **Verify Environment Variables:**
   - Make sure all variables are set (no typos!)
   - Check that values don't have extra spaces

3. **Check Build Logs:**
   - Look for Python version issues
   - Check if all dependencies installed correctly

---

## 📞 Need Help?

- Render Docs: https://render.com/docs
- Check your service logs in Render Dashboard
- Verify all environment variables are set correctly


