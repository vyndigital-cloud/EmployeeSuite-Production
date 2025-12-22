# 🚀 Enable Render Auto-Deployment

## Quick Setup (2 minutes)

### Step 1: Verify Code is Ready
```bash
./verify_auto_deploy.sh
```

### Step 2: Enable in Render Dashboard

1. **Go to Render Dashboard:**
   - https://dashboard.render.com
   - Login to your account

2. **Select Your Web Service:**
   - Click on your service (e.g., `employeesuite-production`)

3. **Go to Settings:**
   - Click **Settings** in the left sidebar
   - Scroll to **Build & Deploy** section

4. **Enable Auto-Deploy:**
   - Find **Auto-Deploy** toggle
   - Set it to **Yes** ✅
   - Verify **Branch** is set to: `main`
   - Verify **GitHub Repo** shows: `vyndigital-cloud/EmployeeSuite-Production`
   - Click **Save Changes**

### Step 3: Test It

```bash
./test_auto_deploy.sh
```

This will:
- Create a test commit
- Push to GitHub
- Trigger auto-deployment in Render

Then check Render Dashboard → **Events** tab to see the deployment start.

---

## Verification Checklist

- [ ] Code is pushed to GitHub (`main` branch)
- [ ] Render service is connected to GitHub repo
- [ ] Auto-Deploy is set to **Yes**
- [ ] Branch is set to **main**
- [ ] Test deployment triggered successfully

---

## Troubleshooting

### Auto-Deploy Not Working?

1. **Check GitHub Connection:**
   - Render Dashboard → Settings → GitHub
   - Verify repo is connected
   - If not, click **Connect GitHub** and reconnect

2. **Check Webhook:**
   - GitHub → Your Repo → Settings → Webhooks
   - Should see a Render webhook
   - If missing, Render will create it when you reconnect

3. **Verify Branch:**
   - Make sure you're pushing to `main` branch
   - Render should be watching `main` branch

4. **Manual Deploy:**
   - If auto-deploy isn't working, use Manual Deploy
   - Render Dashboard → Your Service → **Manual Deploy** → **Deploy latest commit**

---

## Expected Behavior

When you push to GitHub:
1. ✅ Render detects the push (10-30 seconds)
2. ✅ Build starts automatically
3. ✅ Logs appear in Render dashboard
4. ✅ Deployment completes in 2-3 minutes
5. ✅ App is live with latest code

---

## Current Status

**GitHub Repo:** `vyndigital-cloud/EmployeeSuite-Production`  
**Branch:** `main`  
**Latest Commit:** Run `git log --oneline -1` to see

**Next:** Enable auto-deploy in Render dashboard (2 minutes)

