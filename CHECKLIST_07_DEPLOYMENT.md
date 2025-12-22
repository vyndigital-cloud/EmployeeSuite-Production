# 🚀 CHECKLIST #7: DEPLOYMENT

**Priority:** 🟡 **HIGH**  
**Status:** ⚠️ **IN PROGRESS**  
**Items:** 15 total

---

## 🌐 Deployment Configuration

### Environment Variables
- [ ] `SHOPIFY_API_KEY` set
- [ ] `SHOPIFY_API_SECRET` set
- [ ] `SHOPIFY_REDIRECT_URI` set
- [ ] `SECRET_KEY` set (32+ characters)
- [ ] `DATABASE_URL` set (auto-provided)
- [ ] `STRIPE_SECRET_KEY` set
- [ ] `STRIPE_WEBHOOK_SECRET` set
- [ ] `SENDGRID_API_KEY` set
- [ ] `CRON_SECRET` set
- [ ] `SENTRY_DSN` set (optional)

### Build Configuration
- [ ] `Procfile` exists and correct
- [ ] `requirements.txt` complete
- [ ] `runtime.txt` specifies Python version
- [ ] Build command works
- [ ] Start command works

### Auto-Deployment
- [ ] GitHub repo connected
- [ ] Auto-deploy enabled
- [ ] Branch set to `main`
- [ ] Webhook configured

---

## 🧪 Verification Commands

```bash
# Check environment variables
render env list  # If using Render CLI

# Check Procfile
cat Procfile

# Check requirements
pip install -r requirements.txt --dry-run

# Test deployment
curl https://employeesuite-production.onrender.com/health
```

---

## 🔧 Auto-Fix Script

Run: `./fix_deployment_issues.sh`

This will:
- Verify all env vars are set
- Check build configuration
- Verify auto-deploy setup
- Fix any deployment issues

---

## ✅ Completion Status

**0/15 items complete**

**Next:** Move to [CHECKLIST #8: Legal & Privacy](CHECKLIST_08_LEGAL.md)

---

**Last Verified:** Not yet verified

