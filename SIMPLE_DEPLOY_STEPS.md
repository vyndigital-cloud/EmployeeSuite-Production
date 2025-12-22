# 🚀 SIMPLE DEPLOYMENT STEPS

## What You Need To Do (3 Steps):

---

## STEP 1: Go to Render Dashboard

1. Open: https://dashboard.render.com
2. Click on your app/service (probably called "employeesuite-production" or similar)
3. Click "Environment" in the left sidebar

---

## STEP 2: Add These 3 Variables

Click "Add Environment Variable" and add these ONE BY ONE:

### Variable 1:
- **Name:** `SECRET_KEY`
- **Value:** Generate one by running this in terminal:
  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
  Copy the output and paste it as the value

### Variable 2:
- **Name:** `SHOPIFY_API_KEY`
- **Value:** Get this from https://partners.shopify.com → Your App → API credentials → API Key

### Variable 3:
- **Name:** `SHOPIFY_API_SECRET`
- **Value:** Get this from https://partners.shopify.com → Your App → API credentials → Client Secret

---

## STEP 3: Deploy

1. In Render, click "Manual Deploy" → "Deploy latest commit"
2. Wait 2-3 minutes
3. Done!

---

## That's It!

Your app is now deployed and ready to use.

---

## How To Check If It Worked:

Visit: https://employeesuite-production.onrender.com/health

If you see: `{"status":"healthy"...}` → It worked! ✅

If you see an error → Check Render logs for what's wrong

---

## Need Help?

Tell me which step you're stuck on and I'll help!
