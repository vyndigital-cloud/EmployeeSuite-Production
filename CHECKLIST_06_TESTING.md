# 🧪 CHECKLIST #6: TESTING

**Priority:** 🟡 **HIGH**  
**Status:** ⚠️ **IN PROGRESS**  
**Items:** 20 total

---

## ✅ Functional Testing

### OAuth Installation
- [ ] Install app in development store
- [ ] OAuth redirect works
- [ ] Callback processes correctly
- [ ] Store saved to database
- [ ] User logged in after install

### Feature Testing
- [ ] Order Processing works
- [ ] Inventory Management works
- [ ] Revenue Analytics works
- [ ] Error messages display correctly
- [ ] CSV exports work

### Webhook Testing
- [ ] Test `customers/data_request` webhook
- [ ] Test `customers/redact` webhook
- [ ] Test `shop/redact` webhook
- [ ] Test `app/uninstall` webhook
- [ ] All return 200 OK
- [ ] HMAC signatures verified

### Billing Testing
- [ ] Subscription page loads
- [ ] Charge creation works
- [ ] Trial period works
- [ ] Payment failure handling
- [ ] Subscription cancellation

---

## 🧪 Verification Commands

```bash
# Run test suite
python3 test_everything.py

# Test OAuth flow
curl -I https://employeesuite-production.onrender.com/auth/install

# Test webhooks (should return 401 without signature)
curl -X POST https://employeesuite-production.onrender.com/webhooks/customers/data_request
```

---

## 🔧 Auto-Fix Script

Run: `./fix_testing_issues.sh`

This will:
- Run all test suites
- Verify OAuth flow
- Test webhooks
- Fix any failing tests

---

## ✅ Completion Status

**0/20 items complete**

**Next:** Move to [CHECKLIST #7: Deployment](CHECKLIST_07_DEPLOYMENT.md)

---

**Last Verified:** Not yet verified

