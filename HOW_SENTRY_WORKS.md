# 🔍 How Sentry Works in Your App

**Complete guide to understanding Sentry error monitoring**

---

## 🎯 What Sentry Does

Sentry automatically captures and alerts you about errors in your production app. Instead of waiting for users to report bugs, you'll know immediately when something breaks.

---

## ⚙️ How It Works

### 1. **Automatic Error Capture**

When an error occurs in your app:

```python
# Example: User tries to process orders but Shopify API fails
@app.route('/api/process_orders')
def api_process_orders():
    try:
        result = process_orders()  # ← If this crashes...
    except Exception as e:
        # Sentry automatically captures this error
        # You get an email alert within seconds
        return jsonify({"error": str(e)}), 500
```

**What happens:**
1. Error occurs in your code
2. Sentry SDK catches it automatically
3. Error is sent to Sentry servers
4. You get an email alert (if configured)
5. Error appears in Sentry dashboard

### 2. **What Gets Captured**

Sentry captures:
- ✅ **Error message** - What went wrong
- ✅ **Stack trace** - Exact line of code that failed
- ✅ **Request details** - URL, method, headers
- ✅ **User context** - Which user experienced it
- ✅ **Environment** - Production, staging, etc.
- ✅ **Breadcrumbs** - What happened before the error
- ✅ **Performance data** - How long requests took

### 3. **Real-Time Alerts**

When an error happens:
- 📧 **Email alert** sent to you (if configured)
- 🔔 **Sentry dashboard** shows the error
- 📊 **Error count** tracked
- 👥 **Affected users** identified

---

## 📊 What You'll See in Sentry

### Dashboard View

When you log into Sentry, you'll see:

1. **Issues List:**
   ```
   Issue #1: Database connection failed
   - Occurred: 5 times in last hour
   - First seen: 2 hours ago
   - Last seen: 5 minutes ago
   - Affected users: 3
   ```

2. **Error Details:**
   - Full stack trace
   - Request information
   - User information
   - Environment details
   - Timeline of events

3. **Performance Metrics:**
   - Response times
   - Slow queries
   - API call performance

---

## 🔧 How It's Integrated in Your App

### Code Integration (Already Done)

In `app.py`, Sentry is initialized like this:

```python
# Initialize Sentry for error monitoring (if DSN is provided)
sentry_dsn = os.getenv('SENTRY_DSN')
if sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FlaskIntegration(),      # Captures Flask errors
            SqlalchemyIntegration(), # Captures database errors
            LoggingIntegration()     # Captures log errors
        ],
        traces_sample_rate=0.1,     # 10% performance monitoring
        environment='production',
    )
```

**What this means:**
- ✅ All Flask errors automatically captured
- ✅ Database errors automatically captured
- ✅ Log errors automatically captured
- ✅ Performance monitoring enabled (10% sample)

### No Code Changes Needed

**You don't need to add any code!** Sentry works automatically:
- ✅ Catches unhandled exceptions
- ✅ Catches handled exceptions (if you want)
- ✅ Tracks performance
- ✅ Monitors database queries

---

## 📧 Email Alerts Setup

### How to Enable Email Alerts

1. Go to **Sentry Dashboard** → Your Project
2. Click **Settings** → **Alerts**
3. Click **"Create Alert Rule"**
4. Configure:
   - **When:** "An issue is created"
   - **Action:** "Send a notification via email"
   - **To:** Your email address
5. Click **"Save Rule"**

### What You'll Receive

When an error occurs, you'll get an email like:

```
Subject: [Sentry] New Issue: Database connection failed

A new issue was created in employee-suite:

Error: Database connection failed
Location: app.py:567 in api_process_orders
First seen: 2 minutes ago
Occurrences: 1

View Issue: https://employee-suite.sentry.io/issues/12345/
```

---

## 🎯 Real-World Examples

### Example 1: Database Error

**What happens:**
```python
# User tries to access dashboard
# Database connection fails
# Sentry captures: "Database connection timeout"
# You get email: "New error in production"
```

**What you see in Sentry:**
- Error: `psycopg2.OperationalError: connection timeout`
- Location: `app.py:567`
- User: `user@example.com`
- Request: `GET /dashboard`

### Example 2: Shopify API Error

**What happens:**
```python
# User tries to process orders
# Shopify API returns 401 (unauthorized)
# Sentry captures: "Shopify API authentication failed"
# You get email: "New error in production"
```

**What you see in Sentry:**
- Error: `requests.exceptions.HTTPError: 401 Unauthorized`
- Location: `shopify_integration.py:45`
- User: `user@example.com`
- Request: `POST /api/process_orders`

### Example 3: Payment Processing Error

**What happens:**
```python
# User tries to subscribe
# Stripe API fails
# Sentry captures: "Stripe payment processing failed"
# You get email: "New error in production"
```

**What you see in Sentry:**
- Error: `stripe.error.APIConnectionError: Network error`
- Location: `billing.py:234`
- User: `user@example.com`
- Request: `POST /billing/subscribe`

---

## 🔍 Monitoring Your App

### Daily Workflow

1. **Check Sentry Dashboard:**
   - Log into Sentry
   - See all errors from last 24 hours
   - Check error frequency
   - See affected users

2. **Investigate Errors:**
   - Click on an error
   - See full stack trace
   - Check request details
   - See user context

3. **Fix and Deploy:**
   - Fix the error in your code
   - Deploy the fix
   - Sentry tracks if error reoccurs

### What to Look For

**Critical Errors:**
- Database connection failures
- Payment processing errors
- Authentication failures
- API integration errors

**Performance Issues:**
- Slow database queries
- Long API response times
- High memory usage

---

## 🎛️ Sentry Features You Get

### 1. **Error Tracking**
- See all errors in one place
- Track error frequency
- See error trends over time

### 2. **Performance Monitoring**
- Track response times
- Identify slow endpoints
- Monitor database query performance

### 3. **Release Tracking**
- See which errors are new
- Track errors by version
- Identify regressions

### 4. **User Context**
- See which users are affected
- Track user-specific errors
- Understand error impact

### 5. **Breadcrumbs**
- See what happened before error
- Track user actions
- Understand error context

---

## 💡 Pro Tips

### 1. Set Up Alert Rules

Create alerts for:
- **High priority issues** - Critical errors
- **New issues** - First time errors
- **Error spikes** - Sudden increase in errors

### 2. Use Release Tracking

When you deploy:
- Set `RELEASE_VERSION` environment variable
- Sentry will track errors by version
- Easy to see if new version introduced bugs

### 3. Add Custom Context

You can add custom information:

```python
import sentry_sdk

# Add user context
sentry_sdk.set_user({"email": user.email, "id": user.id})

# Add custom tags
sentry_sdk.set_tag("shop_url", shop_url)

# Add custom data
sentry_sdk.set_context("subscription", {
    "is_subscribed": user.is_subscribed,
    "trial_active": user.is_trial_active()
})
```

---

## 📊 Free Tier Limits

**What you get (free):**
- ✅ 5,000 events/month
- ✅ Unlimited projects
- ✅ Email alerts
- ✅ Basic performance monitoring
- ✅ 30 days of error history

**When to upgrade:**
- If you exceed 5,000 events/month
- Need longer error history (90 days)
- Want more advanced features
- Team plan: $26/month (unlimited events)

---

## ✅ Summary

**Sentry works automatically:**
1. ✅ Errors are captured automatically
2. ✅ You get email alerts
3. ✅ Dashboard shows all errors
4. ✅ Performance is monitored
5. ✅ No code changes needed

**What you need to do:**
1. ✅ DSN added to Render (you did this!)
2. ✅ App redeployed (done!)
3. ⏳ Set up email alerts (optional but recommended)
4. ⏳ Check Sentry dashboard regularly

**That's it!** Sentry is now monitoring your app 24/7. 🎉

---

**Last Updated:** January 6, 2025

