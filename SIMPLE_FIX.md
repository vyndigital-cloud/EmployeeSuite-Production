# 🔥 SIMPLE FIX - Stop The Frustration

## The Real Problem

Shopify's OAuth is being picky. Let's fix it the **easiest way possible**.

---

## ✅ Option 1: Install Via Partners Dashboard (EASIEST)

**Skip the URL bullshit entirely:**

1. Go to: https://partners.shopify.com
2. Click **"Stores"** in the left menu
3. Click on **`testsuite-dev`** (your test store)
4. Go to **"Apps"** tab at the top
5. Find **"Employee Suite"** in the list
6. Click **"Install"** or **"Test app"**

**This bypasses all the OAuth URL nonsense and just works.**

---

## ✅ Option 2: If That Doesn't Work - Check These 3 Things

### 1. Is the redirect URI added?

**Partners Dashboard** → Your App → **App Setup** → Scroll to **"Allowed redirection URLs"**

Add this EXACT URL (copy-paste it):
```
https://employeesuite-production.onrender.com/auth/callback
```

Click **"Save"**

### 2. Is the app in Development mode?

**Partners Dashboard** → Your App → **Overview**

Should say **"Development"** or **"Unlisted"** (NOT "Published")

### 3. Does the API Key match?

The `client_id` in your URL is: `396cbab849f7c25996232ea4feda696a`

**Partners Dashboard** → Your App → **App Setup** → **Client credentials**

The **API Key** should match this exactly.

---

## 🎯 If STILL Not Working

**Just tell me:**
1. What error message do you see? (exact text)
2. Did you add the redirect URI?
3. What does Partners Dashboard → Your App → Overview show? (Development/Published/etc)

**OR just use Option 1 above - install via Partners Dashboard. It's way easier.**

---

## 💡 Why This Is Annoying

Shopify's OAuth is strict about:
- Exact redirect URI matching (no trailing slashes, exact domain)
- App status (must be Development for test stores)
- API key matching

That's why installing via Partners Dashboard is easier - it handles all this automatically.

---

## ✅ Try Option 1 First

**Just install via Partners Dashboard. It'll work.**
