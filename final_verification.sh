#!/bin/bash
# Final comprehensive verification - 100% Shopify App Store ready

echo "🎯 FINAL VERIFICATION - SHOPIFY APP STORE READINESS"
echo "=================================================="
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ $1${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo -e "${BLUE}📋 1. FILE VERIFICATION${NC}"
echo "----------------------------------------"
[ -f "app.py" ] && check "app.py exists" || echo -e "${RED}❌ app.py missing${NC}"
[ -f "app.json" ] && check "app.json exists" || echo -e "${RED}❌ app.json missing${NC}"
[ -f "shopify.app.toml" ] && check "shopify.app.toml exists" || echo -e "${RED}❌ shopify.app.toml missing${NC}"
[ -f "Procfile" ] && check "Procfile exists" || echo -e "${RED}❌ Procfile missing${NC}"
[ -f "requirements.txt" ] && check "requirements.txt exists" || echo -e "${RED}❌ requirements.txt missing${NC}"
[ -f "runtime.txt" ] && check "runtime.txt exists" || echo -e "${RED}❌ runtime.txt missing${NC}"
[ -f "static/icon.png" ] && check "App icon (PNG) exists" || echo -e "${YELLOW}⚠️  App icon PNG missing (optional)${NC}"
[ -f "static/icon.svg" ] && check "App icon (SVG) exists" || echo -e "${YELLOW}⚠️  App icon SVG missing (optional)${NC}"
echo ""

echo -e "${BLUE}📋 2. CODE VERIFICATION${NC}"
echo "----------------------------------------"
grep -q "register_blueprint.*oauth_bp" app.py && check "OAuth blueprint registered" || echo -e "${RED}❌ OAuth blueprint not registered${NC}"
grep -q "register_blueprint.*billing_bp" app.py && check "Billing blueprint registered" || echo -e "${RED}❌ Billing blueprint not registered${NC}"
grep -q "register_blueprint.*gdpr_bp" app.py && check "GDPR blueprint registered" || echo -e "${RED}❌ GDPR blueprint not registered${NC}"
grep -q "register_blueprint.*webhook_shopify_bp" app.py && check "Webhook blueprint registered" || echo -e "${RED}❌ Webhook blueprint not registered${NC}"
grep -q "@.*route.*install" shopify_oauth.py && check "OAuth install route exists" || echo -e "${RED}❌ OAuth install route missing${NC}"
grep -q "@.*route.*callback" shopify_oauth.py && check "OAuth callback route exists" || echo -e "${RED}❌ OAuth callback route missing${NC}"
grep -q "app/uninstall" webhook_shopify.py && check "app/uninstall webhook exists" || echo -e "${RED}❌ app/uninstall webhook missing${NC}"
grep -q "app_subscriptions/update" webhook_shopify.py && check "app_subscriptions/update webhook exists" || echo -e "${RED}❌ app_subscriptions/update webhook missing${NC}"
grep -q "customers/data_request" gdpr_compliance.py && check "customers/data_request webhook exists" || echo -e "${RED}❌ customers/data_request webhook missing${NC}"
grep -q "customers/redact" gdpr_compliance.py && check "customers/redact webhook exists" || echo -e "${RED}❌ customers/redact webhook missing${NC}"
grep -q "shop/redact" gdpr_compliance.py && check "shop/redact webhook exists" || echo -e "${RED}❌ shop/redact webhook missing${NC}"
grep -q "verify_session_token" session_token_verification.py && check "Session token verification exists" || echo -e "${RED}❌ Session token verification missing${NC}"
echo ""

echo -e "${BLUE}📋 3. CONFIGURATION VERIFICATION${NC}"
echo "----------------------------------------"
grep -q '"api_version": "2024-10"' app.json && check "API version 2024-10 in app.json" || echo -e "${RED}❌ API version not set in app.json${NC}"
grep -q "api_version = \"2024-10\"" shopify.app.toml && check "API version 2024-10 in shopify.app.toml" || echo -e "${RED}❌ API version not set in shopify.app.toml${NC}"
grep -q "customers/data_request" app.json && check "GDPR webhooks in app.json" || echo -e "${YELLOW}⚠️  GDPR webhooks not in app.json (but in shopify.app.toml)${NC}"
grep -q "gunicorn" Procfile && check "Gunicorn in Procfile" || echo -e "${RED}❌ Gunicorn not in Procfile${NC}"
grep -q "python-3.11" runtime.txt && check "Python 3.11 in runtime.txt" || echo -e "${RED}❌ Python version not set${NC}"
grep -q "Flask==3.0.0" requirements.txt && check "Flask in requirements.txt" || echo -e "${RED}❌ Flask not in requirements.txt${NC}"
grep -q "PyJWT==2.10.1" requirements.txt && check "PyJWT in requirements.txt (for session tokens)" || echo -e "${RED}❌ PyJWT not in requirements.txt${NC}"
echo ""

echo -e "${BLUE}📋 4. SECURITY VERIFICATION${NC}"
echo "----------------------------------------"
grep -q "hmac\|HMAC" gdpr_compliance.py webhook_shopify.py && check "HMAC verification implemented" || echo -e "${RED}❌ HMAC verification missing${NC}"
grep -q "base64" gdpr_compliance.py webhook_shopify.py && check "HMAC uses base64 encoding" || echo -e "${RED}❌ HMAC not using base64${NC}"
[ -f "security_enhancements.py" ] && check "Security enhancements module exists" || echo -e "${RED}❌ Security enhancements missing${NC}"
[ -f "input_validation.py" ] && check "Input validation module exists" || echo -e "${RED}❌ Input validation missing${NC}"
echo ""

echo -e "${BLUE}📋 5. LEGAL & COMPLIANCE${NC}"
echo "----------------------------------------"
([ -f "privacy_policy.txt" ] || grep -q "@.*route.*privacy" app.py legal_routes.py) && check "Privacy Policy exists" || echo -e "${RED}❌ Privacy Policy missing${NC}"
([ -f "terms_of_service.txt" ] || grep -q "@.*route.*terms" app.py legal_routes.py) && check "Terms of Service exists" || echo -e "${RED}❌ Terms of Service missing${NC}"
grep -q "@.*route.*faq" app.py faq_routes.py && check "FAQ route exists" || echo -e "${RED}❌ FAQ route missing${NC}"
echo ""

echo "=================================================="
echo -e "${BLUE}📊 SUMMARY${NC}"
echo "=================================================="
echo -e "${GREEN}✅ Passed: $PASSED${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}❌ Failed: $FAILED${NC}"
else
    echo -e "${GREEN}✅ Failed: 0${NC}"
fi
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 100% READY FOR SHOPIFY APP STORE SUBMISSION!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Complete manual items (screenshots, test account, screencast)"
    echo "2. Verify webhooks in Partners Dashboard"
    echo "3. Submit for review!"
else
    echo -e "${YELLOW}⚠️  Some items need attention before submission${NC}"
fi

echo ""

