# 🚀 QUICK DEPLOY INSTRUCTIONS - Option 1

## Step 1: Install Node.js (if needed)

You need Node.js to use Shopify CLI. Install it:

```bash
brew install node
```

Or download from: https://nodejs.org/

## Step 2: Install Shopify CLI

```bash
npm install -g @shopify/cli @shopify/theme
```

## Step 3: Deploy

```bash
cd /Users/essentials/Documents/1EmployeeSuite-FIXED
shopify app deploy --no-release
```

**OR use the automated script:**
```bash
./DEPLOY_WEBHOOKS.sh
```

---

## ✅ After Deployment

1. Wait 2-3 minutes
2. Go to **Shopify Partners Dashboard** → **Distribution**
3. Click **"Run"** to re-run automated checks
4. Webhook compliance errors should be resolved ✅

---

## 🎯 Alternative: Use Programmatic Registration (Option 2)

If you can't install Shopify CLI right now, the webhooks will automatically register when someone installs your app via OAuth. However, Shopify's automated checks won't pass until the webhooks are registered.

**Best option:** Install Node.js → Install Shopify CLI → Deploy
