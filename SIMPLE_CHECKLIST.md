# ✅ SIMPLE CHECKLIST - Do These 3 Things

## Step 1: Deploy Webhooks (Do This First)

Open your terminal and run:

```bash
cd /Users/essentials/.cursor/worktrees/1EmployeeSuite-FIXED/bms
shopify app deploy
```

**What to expect:**
- It might ask you to confirm (type `y` or press Enter)
- You might see a warning about `package.json` - **IGNORE IT** (this is normal for Python apps)
- Look for messages like "Successfully deployed" or "Webhooks registered"

**If it asks questions, answer them.**
**If it shows an error, copy the error and tell me.**

---

## Step 2: Check Partners Dashboard (After Step 1)

1. Go to: https://partners.shopify.com
2. Log in if needed
3. Click **Apps** (left sidebar)
4. Click **Employee Suite**
5. Click **App Setup** (left sidebar)
6. Scroll down to find **"Webhooks"** section

**What to look for:**
- Do you see a list of webhooks?
- Do you see these 3 listed?
  - customers/data_request
  - customers/redact
  - shop/redact

**Tell me:**
- ✅ YES, I see them listed
- ❌ NO, I don't see any webhooks
- ❌ I can't find the "Webhooks" section

---

## Step 3: Run Automated Checks (After Step 2)

1. Still in Partners Dashboard
2. Click **Distribution** tab (top of the page)
3. Click the **"Run"** button (usually near the top)
4. Wait 1-2 minutes for results

**What you'll see:**
- A list of checks with ✅ (pass) or ❌ (fail)
- Look for these two:
  - "Provides mandatory compliance webhooks"
  - "Verifies webhooks with HMAC signatures"

**Tell me:**
- ✅ Both show as PASS
- ❌ One or both show as FAIL
- ❌ I see error messages (copy them exactly)

---

## That's It!

Just do these 3 steps and tell me what you see at each step. Don't worry about anything else right now.

**Start with Step 1** - run `shopify app deploy` and tell me what happens.
