# 🚀 DEPLOYMENT-READY CHECKLIST

**Status:** ✅ **READY FOR PRODUCTION DEPLOYMENT**

---

## ✅ Pre-Deployment Verification

### Code Quality
- [x] No hardcoded secrets (all use `os.getenv()`)
- [x] No debug mode in production code
- [x] All error handling in place
- [x] Security headers configured
- [x] Input validation on all user inputs
- [x] SQL injection protection (via ORM)
- [x] XSS prevention implemented

### Configuration Files
- [x] `Procfile` - Gunicorn configuration (4 workers, 4 threads)
- [x] `runtime.txt` - Python 3.11 specified
- [x] `requirements.txt` - All dependencies listed
- [x] `shopify.app.toml` - Shopify app configuration
- [x] `app.json` - App manifest

---

## 🔐 REQUIRED Environment Variables

### **CRITICAL - Must Set Before Deployment:**

```bash
# Security (REQUIRED)
SECRET_KEY=<generate-random-32-char-string>
CRON_SECRET=<generate-random-32-char-string>

# Database (Auto-provided by Render)
DATABASE_URL=postgresql://... (Render provides this automatically)

# Shopify App Store (REQUIRED for App Store)
SHOPIFY_API_KEY=<from-partners-dashboard>
SHOPIFY_API_SECRET=<from-partners-dashboard>
SHOPIFY_REDIRECT_URI=https://employeesuite-production.onrender.com/auth/callback
APP_DOMAIN=employeesuite-production.onrender.com

# Stripe Billing (REQUIRED for payments)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_MONTHLY_PRICE_ID=price_...

# Email (REQUIRED for notifications)
SENDGRID_API_KEY=SG....
```

### **OPTIONAL - Recommended for Production:**

```bash
# Monitoring
SENTRY_DSN=https://your-key@sentry.io/project-id
ENVIRONMENT=production
RELEASE_VERSION=1.0.0

# Database Backups
S3_BACKUP_BUCKET=your-bucket-name
S3_BACKUP_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
BACKUP_RETENTION_DAYS=30
```

---

## 📋 Deployment Steps

### Step 1: Generate Secrets

```bash
# Generate SECRET_KEY (32+ characters)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate CRON_SECRET (32+ characters)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 2: Set Environment Variables in Render

1. Go to Render Dashboard → Your Service → Environment
2. Add each variable from the REQUIRED list above
3. **CRITICAL:** Make sure `SECRET_KEY` is set (app will fail to start without it in production)

### Step 3: Verify Configuration

**Check these in Render:**
- [ ] `SECRET_KEY` is set (not empty)
- [ ] `DATABASE_URL` is set (auto-provided)
- [ ] `SHOPIFY_API_KEY` matches Partners Dashboard
- [ ] `SHOPIFY_API_SECRET` matches Partners Dashboard
- [ ] `STRIPE_SECRET_KEY` is set (if using Stripe)
- [ ] `SENDGRID_API_KEY` is set (if using email)

### Step 4: Deploy

1. Push code to GitHub (if auto-deploy enabled)
2. Or manually trigger deployment in Render
3. Watch logs for startup errors
4. Verify app starts successfully

### Step 5: Post-Deployment Verification

**Health Check:**
```bash
curl https://employeesuite-production.onrender.com/health
```
Expected: `{"status":"healthy","service":"Employee Suite","version":"2.0","database":"connected"}`

**Test OAuth:**
1. Visit: `https://employeesuite-production.onrender.com/settings/shopify`
2. Enter shop domain
3. Click "Connect with Shopify"
4. Should redirect to Shopify OAuth

**Test Webhooks:**
```bash
curl -X POST https://employeesuite-production.onrender.com/webhooks/customers/data_request \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Hmac-Sha256: test" \
  -d '{"test": "data"}'
```
Expected: `{"error": "Invalid signature"}` (401) - This means endpoint exists and is working

---

## 🔒 Security Checklist

- [x] No secrets in code
- [x] SECRET_KEY validation (fails fast if missing in production)
- [x] Debug mode disabled in production
- [x] Secure cookies (HTTPS only)
- [x] HttpOnly cookies
- [x] SameSite cookie protection
- [x] CSRF protection (Flask-Login + secure sessions)
- [x] Rate limiting enabled
- [x] Input validation on all routes
- [x] XSS prevention
- [x] SQL injection protection
- [x] Webhook HMAC verification

---

## 🧪 Testing Checklist

### Before Going Live:
- [ ] Health endpoint returns 200
- [ ] Dashboard loads without errors
- [ ] OAuth flow works (test with dev store)
- [ ] Webhooks respond (even if signature fails, endpoint should exist)
- [ ] Error pages display correctly (404, 500)
- [ ] Database migrations run successfully
- [ ] No errors in Render logs

### After Deployment:
- [ ] Test app installation in Shopify
- [ ] Verify webhooks are registered
- [ ] Test order processing
- [ ] Test inventory check
- [ ] Test revenue report
- [ ] Verify email delivery (if SendGrid configured)
- [ ] Check Sentry for errors (if configured)

---

## 🚨 Common Deployment Issues

### Issue: "SECRET_KEY is REQUIRED"
**Solution:** Set `SECRET_KEY` environment variable in Render

### Issue: Database connection fails
**Solution:** Verify `DATABASE_URL` is set (Render provides this automatically)

### Issue: OAuth redirect fails
**Solution:** 
1. Check `SHOPIFY_REDIRECT_URI` matches Partners Dashboard
2. Verify `SHOPIFY_API_KEY` and `SHOPIFY_API_SECRET` are correct

### Issue: Webhooks return 401
**Solution:** 
1. Verify `SHOPIFY_API_SECRET` is set correctly
2. Check webhook HMAC verification is working

### Issue: App crashes on startup
**Solution:**
1. Check Render logs for error messages
2. Verify all REQUIRED environment variables are set
3. Check `requirements.txt` dependencies are installed

---

## 📊 Production Monitoring

### Recommended Setup:

1. **Sentry Error Monitoring:**
   - Set `SENTRY_DSN` environment variable
   - Monitor errors in real-time
   - Get email alerts for critical errors

2. **Render Logs:**
   - Monitor application logs
   - Watch for errors or warnings
   - Check webhook delivery

3. **Health Checks:**
   - Set up external monitoring (UptimeRobot, etc.)
   - Monitor `/health` endpoint
   - Alert on downtime

4. **Database Backups:**
   - Set up S3 backup variables
   - Configure cron job for daily backups
   - Verify backups are being created

---

## ✅ Final Pre-Launch Checklist

- [ ] All REQUIRED environment variables set
- [ ] Health endpoint working
- [ ] OAuth flow tested
- [ ] Webhooks responding
- [ ] Error pages working
- [ ] No errors in logs
- [ ] Database migrations successful
- [ ] Security headers active
- [ ] Rate limiting working
- [ ] Monitoring configured (Sentry recommended)

---

## 🎯 Post-Deployment

### First 24 Hours:
1. Monitor Render logs closely
2. Check Sentry for any errors
3. Test all major features
4. Verify webhook deliveries
5. Test with real Shopify store

### First Week:
1. Monitor error rates
2. Check user feedback
3. Verify payment processing (if applicable)
4. Monitor database performance
5. Review security logs

---

## 📞 Support Resources

- **Render Docs:** https://render.com/docs
- **Shopify Partner Docs:** https://shopify.dev/docs/apps
- **Flask Docs:** https://flask.palletsprojects.com
- **Gunicorn Docs:** https://docs.gunicorn.org

---

**Status: ✅ READY FOR DEPLOYMENT**

All code is production-ready. Set environment variables and deploy!
