# 🔔 CHECKLIST #4: WEBHOOKS

**Priority:** 🔴 **CRITICAL**  
**Status:** ⚠️ **IN PROGRESS**  
**Items:** 12 total

---

## 📡 Mandatory Webhooks

### GDPR Compliance Webhooks
- [ ] `customers/data_request` - Route exists and works
- [ ] `customers/redact` - Route exists and works
- [ ] `shop/redact` - Route exists and works
- [x] All return 200 OK within 5 seconds
- [ ] All verify HMAC signatures

### App Lifecycle Webhooks
- [ ] `app/uninstall` - Handles app removal
- [ ] `app_subscriptions/update` - Handles billing updates
- [ ] Both verify HMAC signatures
- [ ] Both return 200 OK

### Webhook Registration
- [ ] All webhooks in `app.json` or `shopify.app.toml`
- [x] Webhooks registered in Partners Dashboard
- [ ] Webhook URLs are correct (HTTPS)
- [ ] Webhook format matches Shopify spec

---

## 🧪 Verification Commands

```bash
# Check webhook routes
grep -r "@app.route.*webhook\|@app.route.*data_request\|@app.route.*redact" gdpr_compliance.py webhook_shopify.py

# Check webhook registration
grep -r "customers/data_request\|customers/redact\|shop/redact" app.json shopify.app.toml

# Test webhook endpoints (should return 401 without signature)
curl -X POST https://employeesuite-production.onrender.com/webhooks/customers/data_request
```

---

## 🔧 Auto-Fix Script

Run: `./fix_webhook_issues.sh`

This will:
- Verify all webhook routes exist
- Check webhook registration
- Verify HMAC verification
- Fix any missing webhooks

---

## ✅ Completion Status

**0/12 items complete**

**Next:** Move to [CHECKLIST #5: App Store Listing](CHECKLIST_05_LISTING.md)

---

**Last Verified:** Not yet verified

