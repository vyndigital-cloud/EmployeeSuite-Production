# ✅ FULL SET & FORGET CHECKLIST - 100% PASSIVE

**Goal:** True passive income - deploy and forget  
**Target:** $500/day = $15,000/month (30 clients)  
**Max Scale:** 50-100 clients  
**Status:** Ready after completing this checklist

---

## 🎯 PRE-DEPLOYMENT CHECKLIST

### ✅ Code & Configuration
- [x] All code tested and working
- [x] All files compile successfully
- [x] Procfile configured (4 workers, 4 threads)
- [x] Database pool optimized (10/20 connections)
- [x] All routes protected with @require_access
- [x] Security headers enabled
- [x] Rate limiting configured
- [x] Error handling on all routes
- [x] Health check endpoint working

---

## 🔐 ENVIRONMENT VARIABLES (Render Dashboard)

### ✅ Required (Must Have):
- [ ] `SECRET_KEY` - Random secret key (32+ characters)
- [ ] `DATABASE_URL` - Auto-provided by Render (PostgreSQL)
- [ ] `STRIPE_SECRET_KEY` - From Stripe dashboard (sk_live_...)
- [ ] `STRIPE_WEBHOOK_SECRET` - From Stripe webhook settings
- [ ] `STRIPE_SETUP_PRICE_ID` - From Stripe products (price_...)
- [ ] `STRIPE_MONTHLY_PRICE_ID` - From Stripe products (price_...)
- [ ] `SENDGRID_API_KEY` - From SendGrid dashboard
- [ ] `CRON_SECRET` - Random secret for cron endpoints (32+ characters)

### ✅ Optional (Recommended):
- [ ] `SENTRY_DSN` - From Sentry.io (error monitoring)
- [ ] `ENVIRONMENT` - Set to `production`
- [ ] `RELEASE_VERSION` - Your app version (e.g., `1.0.0`)
- [ ] `S3_BACKUP_BUCKET` - AWS S3 bucket name (for backups)
- [ ] `S3_BACKUP_REGION` - AWS region (e.g., `us-east-1`)
- [ ] `AWS_ACCESS_KEY_ID` - AWS IAM user access key
- [ ] `AWS_SECRET_ACCESS_KEY` - AWS IAM user secret key
- [ ] `BACKUP_RETENTION_DAYS` - Backup retention (default: 30)
- [ ] `SHOPIFY_API_KEY` - From Shopify Partner dashboard
- [ ] `SHOPIFY_API_SECRET` - From Shopify Partner dashboard
- [ ] `SHOPIFY_REDIRECT_URI` - Your callback URL

---

## 🤖 AUTOMATED SYSTEMS (Verify Working)

### ✅ 1. Trial Management
- [x] Trial expiration auto-lockout (code implemented)
- [x] Trial warning emails (code implemented)
- [ ] **External cron job set up** (cron-job.org) ⚠️ SETUP NEEDED
  - URL: `https://employeesuite-production.onrender.com/cron/send-trial-warnings?secret=YOUR_CRON_SECRET`
  - Schedule: Daily at 9:00 AM UTC
  - Status: ⚠️ Needs external setup

### ✅ 2. Payment Processing
- [x] Stripe webhooks configured
- [x] Payment success handling (auto)
- [x] Payment failure handling (auto)
- [x] Subscription renewal (auto)
- [x] Subscription cancellation (auto)
- [ ] **Stripe webhook endpoint verified** ⚠️ VERIFY
  - URL: `https://employeesuite-production.onrender.com/webhook/stripe`
  - Events: `invoice.payment_failed`, `invoice.payment_succeeded`, `customer.subscription.deleted`, `customer.subscription.updated`
  - Status: ⚠️ Verify in Stripe dashboard

### ✅ 3. Email Automation
- [x] Welcome emails (auto on registration)
- [x] Trial warnings (auto via cron)
- [x] Payment confirmations (auto via webhooks)
- [x] Payment failures (auto via webhooks)
- [x] Cancellation emails (auto)
- [x] Password reset emails (auto)
- [ ] **SendGrid API key verified** ⚠️ VERIFY
  - Test email sent successfully
  - Status: ⚠️ Test after deployment

### ✅ 4. Database Management
- [x] Auto-initialization on startup
- [x] Auto-migrations on startup
- [x] Connection pooling configured
- [x] Backup system implemented
- [ ] **External cron job for backups** (cron-job.org) ⚠️ SETUP NEEDED
  - URL: `https://employeesuite-production.onrender.com/cron/database-backup?secret=YOUR_CRON_SECRET`
  - Schedule: Daily at 2:00 AM UTC
  - Status: ⚠️ Needs external setup (if using S3 backups)

### ✅ 5. Error Monitoring
- [x] Sentry integration (code implemented)
- [ ] **Sentry DSN configured** ⚠️ SETUP NEEDED
  - Create account at sentry.io
  - Get DSN
  - Add to Render environment variables
  - Status: ⚠️ Optional but recommended

### ✅ 6. Security
- [x] Rate limiting (200 req/hour)
- [x] Input validation (all forms)
- [x] Security headers (all responses)
- [x] Secure cookies (HTTPS-only)
- [x] CSRF protection
- [x] XSS prevention
- [x] SQL injection protection
- [x] Webhook signature verification
- Status: ✅ Fully automated

### ✅ 7. Webhook Handling
- [x] Stripe webhooks (auto)
- [x] Shopify webhooks (auto)
- [x] GDPR webhooks (auto)
- [ ] **Shopify webhooks configured** ⚠️ VERIFY
  - App uninstall webhook
  - Subscription update webhook
  - GDPR webhooks (data_request, redact)
  - Status: ⚠️ Verify in Shopify Partner dashboard

---

## 📊 MONITORING & ALERTS

### ✅ 1. Uptime Monitoring ⚠️ SETUP NEEDED
- [ ] **UptimeRobot account created** (uptimerobot.com)
- [ ] **Monitor added:**
  - URL: `https://employeesuite-production.onrender.com/health`
  - Interval: 5 minutes
  - Alert: Email + SMS (optional)
- [ ] **Test alert received** (verify it works)
- Status: ⚠️ 5 minutes to set up

### ✅ 2. Error Monitoring
- [x] Sentry integration (code ready)
- [ ] **Sentry account created** (sentry.io)
- [ ] **DSN added to Render**
- [ ] **Test error sent** (verify it appears in Sentry)
- [ ] **Email alerts configured** (Sentry settings)
- Status: ⚠️ Optional but recommended

### ✅ 3. Health Checks
- [x] `/health` endpoint implemented
- [x] Database connectivity check
- [x] Auto-restart on failure (Render feature)
- Status: ✅ Ready

---

## 🗄️ DATABASE & BACKUPS

### ✅ Database
- [x] PostgreSQL configured (Render auto-provides)
- [x] Connection pooling (10/20)
- [x] Auto-initialization
- [x] Auto-migrations
- [x] Indexes created
- Status: ✅ Ready

### ✅ Backups
- [x] Backup system implemented
- [x] S3 integration ready
- [ ] **AWS S3 bucket created** (if using backups)
- [ ] **AWS IAM user created** (S3 access only)
- [ ] **AWS credentials added to Render**
- [ ] **Backup cron job configured** (cron-job.org)
- [ ] **Test backup successful** (verify file in S3)
- Status: ⚠️ Optional but recommended

---

## 🔗 EXTERNAL SERVICES

### ✅ 1. Stripe
- [ ] **Account created** (stripe.com)
- [ ] **Products created:**
  - Setup fee: $1,000 (one-time)
  - Monthly subscription: $500 (recurring)
- [ ] **Price IDs copied** (add to Render env vars)
- [ ] **Webhook endpoint configured:**
  - URL: `https://employeesuite-production.onrender.com/webhook/stripe`
  - Events: All payment/subscription events
- [ ] **Webhook secret copied** (add to Render env vars)
- [ ] **Test payment successful** (verify webhook works)
- Status: ⚠️ Verify all configured

### ✅ 2. SendGrid
- [ ] **Account created** (sendgrid.com)
- [ ] **API key created** (full access)
- [ ] **API key added to Render**
- [ ] **Sender verified** (adam@golproductions.com)
- [ ] **Test email sent** (verify delivery)
- Status: ⚠️ Verify all configured

### ✅ 3. Shopify
- [ ] **Partner account created** (partners.shopify.com)
- [ ] **App created in Partner dashboard**
- [ ] **OAuth credentials:**
  - API Key (add to Render)
  - API Secret (add to Render)
- [ ] **Webhooks configured:**
  - App uninstall
  - Subscription update
  - GDPR webhooks
- [ ] **Billing API configured**
- [ ] **Test OAuth flow** (verify installation works)
- Status: ⚠️ Verify all configured

### ✅ 4. External Cron Service
- [ ] **Account created** (cron-job.org - free)
- [ ] **Trial warnings job:**
  - URL: `https://employeesuite-production.onrender.com/cron/send-trial-warnings?secret=YOUR_CRON_SECRET`
  - Schedule: Daily 9:00 AM UTC
- [ ] **Database backup job:**
  - URL: `https://employeesuite-production.onrender.com/cron/database-backup?secret=YOUR_CRON_SECRET`
  - Schedule: Daily 2:00 AM UTC
- [ ] **Test jobs executed** (verify they work)
- Status: ⚠️ 5 minutes to set up

---

## 🚀 DEPLOYMENT

### ✅ Render.com Setup
- [ ] **Service created** (Web Service)
- [ ] **GitHub connected**
- [ ] **Repository selected**
- [ ] **Build command:** `pip install -r requirements.txt` (or `bash build.sh`)
- [ ] **Start command:** Auto-detected (gunicorn app:app)
- [ ] **Environment variables:** All added (see checklist above)
- [ ] **Database:** PostgreSQL added (auto)
- [ ] **Deployment:** Successful
- [ ] **Health check:** `/health` returns 200
- Status: ⚠️ Verify deployment successful

---

## ✅ POST-DEPLOYMENT VERIFICATION

### ✅ 1. Basic Functionality
- [ ] **Home page loads** (`/`)
- [ ] **Dashboard loads** (`/dashboard`)
- [ ] **Health check works** (`/health` returns healthy)
- [ ] **Login works** (`/login`)
- [ ] **Registration works** (`/register`)
- [ ] **Subscribe page loads** (`/subscribe`)

### ✅ 2. Core Features
- [ ] **Order monitoring works** (click "View Orders")
- [ ] **Inventory check works** (click "Check Inventory")
- [ ] **Revenue report works** (click "Generate Report")
- [ ] **CSV export works** (click "Export CSV" on report)

### ✅ 3. Payment Flow
- [ ] **Subscribe button works** (redirects to Stripe)
- [ ] **Stripe checkout loads** (verify pricing correct)
- [ ] **Payment success** (test with Stripe test card)
- [ ] **Webhook received** (check Stripe dashboard)
- [ ] **User access granted** (can use features after payment)

### ✅ 4. Automation
- [ ] **Welcome email sent** (check email after registration)
- [ ] **Trial warning sent** (test cron job manually)
- [ ] **Payment confirmation sent** (check email after payment)
- [ ] **Database backup works** (test cron job manually)

### ✅ 5. Security
- [ ] **HTTPS enforced** (check browser shows lock)
- [ ] **Security headers present** (check browser dev tools)
- [ ] **Rate limiting works** (make 201 requests, should get 429)
- [ ] **Trial lockout works** (wait for trial to expire, verify redirect)

---

## 📋 LEGAL & COMPLIANCE

### ✅ Legal Pages
- [x] Privacy Policy (`/privacy`)
- [x] Terms of Service (`/terms`)
- [x] FAQ (`/faq`)
- [x] All pages accessible
- [x] All content accurate

### ✅ Compliance
- [x] GDPR webhooks implemented
- [x] Data deletion handlers
- [x] Data request handlers
- [x] Terms updated for Perth, WA + international
- [x] Refund policy clear and fair

---

## 🎯 FINAL VERIFICATION

### ✅ Performance
- [ ] **Page load time:** < 2 seconds
- [ ] **API response time:** < 1 second
- [ ] **Database queries:** Optimized
- [ ] **Caching working:** Verify cache hits

### ✅ Scalability
- [ ] **Workers:** 4 (verified in Procfile)
- [ ] **Threads:** 4 per worker
- [ ] **DB Pool:** 10/20 (verified in app.py)
- [ ] **Can handle:** 50-100 clients

### ✅ Monitoring
- [ ] **Uptime monitoring:** Active
- [ ] **Error monitoring:** Active (Sentry)
- [ ] **Health checks:** Working
- [ ] **Alerts configured:** Email/SMS

---

## 🚨 EMERGENCY CONTACTS & INFO

### If Something Breaks:
1. **Check Render logs** - Dashboard → Logs
2. **Check Sentry** - Error dashboard
3. **Check UptimeRobot** - Uptime status
4. **Check Stripe** - Payment issues
5. **Check SendGrid** - Email delivery

### Quick Fixes:
- **App down:** Render auto-restarts (check health endpoint)
- **Payment issues:** Check Stripe webhook logs
- **Email issues:** Check SendGrid dashboard
- **Database issues:** Check Render database logs

---

## ✅ COMPLETION CHECKLIST

### Must Complete (For Passive):
- [ ] All environment variables set
- [ ] Stripe webhooks configured
- [ ] SendGrid verified
- [ ] Uptime monitoring active
- [ ] External cron jobs configured
- [ ] All features tested
- [ ] Payment flow tested
- [ ] Email automation tested

### Optional (For Better Monitoring):
- [ ] Sentry configured
- [ ] S3 backups configured
- [ ] Slack alerts (Sentry)

---

## 🎯 WHEN YOU'RE DONE

**You'll have:**
- ✅ Fully automated system
- ✅ 95% passive operation
- ✅ Handles 50-100 clients
- ✅ Auto-recovery from issues
- ✅ Know about problems immediately
- ✅ $500/day = $15,000/month revenue
- ✅ True set & forget operation

**Time to Complete:** 30-60 minutes  
**Cost:** $0-15/month (mostly free)  
**Result:** True passive income 🚀

---

## 📝 QUICK REFERENCE

### Critical URLs:
- **App:** `https://employeesuite-production.onrender.com`
- **Health:** `https://employeesuite-production.onrender.com/health`
- **Stripe Webhook:** `https://employeesuite-production.onrender.com/webhook/stripe`
- **Trial Cron:** `https://employeesuite-production.onrender.com/cron/send-trial-warnings?secret=YOUR_SECRET`
- **Backup Cron:** `https://employeesuite-production.onrender.com/cron/database-backup?secret=YOUR_SECRET`

### External Services:
- **UptimeRobot:** https://uptimerobot.com
- **Cron Jobs:** https://cron-job.org
- **Sentry:** https://sentry.io
- **Stripe:** https://dashboard.stripe.com
- **SendGrid:** https://app.sendgrid.com
- **Shopify Partners:** https://partners.shopify.com

---

**Complete this checklist and you're 100% set & forget ready!** ✅
