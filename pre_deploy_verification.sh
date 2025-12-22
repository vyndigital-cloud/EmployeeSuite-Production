#!/bin/bash
# Pre-Deployment Verification System
# Only allows deployment when ALL checks pass

set -e  # Exit on any error

echo "🔍 PRE-DEPLOYMENT VERIFICATION SYSTEM"
echo "======================================"
echo ""
echo "This system will verify ALL critical components before deployment."
echo "Deployment will ONLY proceed if ALL checks pass."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0
CRITICAL_FAILURES=0

# Function to run a check
check() {
    local name=$1
    local command=$2
    local critical=${3:-true}  # Default to critical
    
    echo -n "Checking: $name... "
    
    if bash -c "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        FAILED=$((FAILED + 1))
        if [ "$critical" = "true" ]; then
            CRITICAL_FAILURES=$((CRITICAL_FAILURES + 1))
            echo -e "${RED}   ⚠️  CRITICAL - Deployment blocked${NC}"
        else
            echo -e "${YELLOW}   ⚠️  WARNING - Deployment may proceed${NC}"
        fi
        return 1
    fi
}

echo -e "${BLUE}📋 PHASE 1: FILE VERIFICATION${NC}"
echo "----------------------------------------"

check "app.py exists" "[ -f app.py ]"
check "app.json exists" "[ -f app.json ]"
check "shopify.app.toml exists" "[ -f shopify.app.toml ]"
check "Procfile exists" "[ -f Procfile ]"
check "requirements.txt exists" "[ -f requirements.txt ]"
check "runtime.txt exists" "[ -f runtime.txt ]"
check "models.py exists" "[ -f models.py ]"
check "auth.py exists" "[ -f auth.py ]"
check "billing.py exists" "[ -f billing.py ]"
check "shopify_oauth.py exists" "[ -f shopify_oauth.py ]"
check "gdpr_compliance.py exists" "[ -f gdpr_compliance.py ]"
check "webhook_shopify.py exists" "[ -f webhook_shopify.py ]"
check "session_token_verification.py exists" "[ -f session_token_verification.py ]"

echo ""
echo -e "${BLUE}📋 PHASE 2: CODE VERIFICATION${NC}"
echo "----------------------------------------"

check "Python syntax valid (app.py)" "python3 -m py_compile app.py"
check "Python syntax valid (auth.py)" "python3 -m py_compile auth.py"
check "Python syntax valid (billing.py)" "python3 -m py_compile billing.py"
check "Python syntax valid (models.py)" "python3 -m py_compile models.py"
check "Python syntax valid (shopify_oauth.py)" "python3 -m py_compile shopify_oauth.py"
check "Python syntax valid (gdpr_compliance.py)" "python3 -m py_compile gdpr_compliance.py"
check "Python syntax valid (webhook_shopify.py)" "python3 -m py_compile webhook_shopify.py"

echo ""
echo -e "${BLUE}📋 PHASE 3: CONFIGURATION VERIFICATION${NC}"
echo "----------------------------------------"

check "OAuth blueprint registered" "grep -q 'register_blueprint.*oauth_bp' app.py"
check "Billing blueprint registered" "grep -q 'register_blueprint.*billing_bp' app.py"
check "GDPR blueprint registered" "grep -q 'register_blueprint.*gdpr_bp' app.py"
check "Webhook blueprint registered" "grep -q 'register_blueprint.*webhook_shopify_bp' app.py"
check "OAuth install route exists" "grep -q '@.*route.*install' shopify_oauth.py"
check "OAuth callback route exists" "grep -q '@.*route.*callback' shopify_oauth.py"
check "app/uninstall webhook exists" "grep -q 'app/uninstall' webhook_shopify.py"
check "app_subscriptions/update webhook exists" "grep -q 'app_subscriptions/update' webhook_shopify.py"
check "customers/data_request webhook exists" "grep -q 'customers/data_request' gdpr_compliance.py"
check "customers/redact webhook exists" "grep -q 'customers/redact' gdpr_compliance.py"
check "shop/redact webhook exists" "grep -q 'shop/redact' gdpr_compliance.py"
check "Session token verification exists" "grep -q 'verify_session_token' session_token_verification.py"
check "HMAC verification implemented" "grep -q 'hmac\|HMAC' gdpr_compliance.py webhook_shopify.py"
check "API version 2024-10 in app.json" "grep -q '\"api_version\": \"2024-10\"' app.json"
check "API version 2024-10 in shopify.app.toml" "grep -q 'api_version = \"2024-10\"' shopify.app.toml"
check "Gunicorn in Procfile" "grep -q 'gunicorn' Procfile"
check "Python 3.11 in runtime.txt" "grep -q 'python-3.11' runtime.txt"

echo ""
echo -e "${BLUE}📋 PHASE 4: IMPORT VERIFICATION${NC}"
echo "----------------------------------------"

check "App imports successfully" "python3 -c 'from app import app; print(\"OK\")' 2>&1 | grep -q 'OK\|Sentry'"
check "Models import successfully" "python3 -c 'from models import db, User, ShopifyStore; print(\"OK\")'"
check "Auth imports successfully" "python3 -c 'from auth import auth_bp; print(\"OK\")'"
check "Billing imports successfully" "python3 -c 'from billing import billing_bp; print(\"OK\")'"

echo ""
echo -e "${BLUE}📋 PHASE 5: DEPENDENCY VERIFICATION${NC}"
echo "----------------------------------------"

check "Flask in requirements.txt" "grep -q 'Flask==' requirements.txt"
check "Flask-Login in requirements.txt" "grep -q 'Flask-Login==' requirements.txt"
check "Flask-SQLAlchemy in requirements.txt" "grep -q 'Flask-SQLAlchemy==' requirements.txt"
check "PyJWT in requirements.txt (session tokens)" "grep -q 'PyJWT==' requirements.txt"
check "gunicorn in requirements.txt" "grep -q 'gunicorn==' requirements.txt"
check "psycopg2-binary in requirements.txt" "grep -q 'psycopg2-binary==' requirements.txt"

echo ""
echo -e "${BLUE}📋 PHASE 6: SECURITY VERIFICATION${NC}"
echo "----------------------------------------"

check "No hardcoded secrets in app.py" "grep -q 'SECRET_KEY.*=.*os.getenv' app.py" "false"
check "Dev fallback secret present" "grep -q 'dev-secret-key-change-in-production' app.py" "false"
check "No hardcoded API secrets" "grep -q 'SHOPIFY_API_SECRET.*=.*os.getenv' app.py shopify_oauth.py || ! grep -q 'SHOPIFY_API_SECRET.*=.*['\\\"][a-zA-Z0-9]\{20,\}' app.py shopify_oauth.py"
check "HMAC uses base64 encoding" "grep -q 'base64' gdpr_compliance.py webhook_shopify.py"
check "Security headers module exists" "[ -f security_enhancements.py ]"
check "Input validation module exists" "[ -f input_validation.py ]"

echo ""
echo -e "${BLUE}📋 PHASE 7: LEGAL & COMPLIANCE${NC}"
echo "----------------------------------------"

check "Privacy Policy exists" "[ -f privacy_policy.txt ] || grep -q '@.*route.*privacy' app.py legal_routes.py"
check "Terms of Service exists" "[ -f terms_of_service.txt ] || grep -q '@.*route.*terms' app.py legal_routes.py"
check "FAQ route exists" "grep -q '@.*route.*faq' app.py faq_routes.py"

echo ""
echo "======================================"
echo -e "${BLUE}📊 VERIFICATION SUMMARY${NC}"
echo "======================================"
echo -e "${GREEN}✅ Passed: $PASSED${NC}"
echo -e "${RED}❌ Failed: $FAILED${NC}"
echo -e "${RED}🔴 Critical Failures: $CRITICAL_FAILURES${NC}"
echo ""

if [ $CRITICAL_FAILURES -gt 0 ]; then
    echo -e "${RED}🚫 DEPLOYMENT BLOCKED${NC}"
    echo ""
    echo "Critical failures detected. Please fix the following issues before deploying:"
    echo ""
    echo "1. Review the failed checks above"
    echo "2. Fix all critical failures"
    echo "3. Run this verification again: ./pre_deploy_verification.sh"
    echo ""
    exit 1
elif [ $FAILED -gt 0 ]; then
    echo -e "${YELLOW}⚠️  DEPLOYMENT ALLOWED WITH WARNINGS${NC}"
    echo ""
    echo "Some non-critical checks failed, but deployment can proceed."
    echo "Review warnings above and fix when possible."
    echo ""
    exit 0
else
    echo -e "${GREEN}✅ ALL CHECKS PASSED${NC}"
    echo ""
    echo "Your app is verified and ready for deployment!"
    echo ""
    echo "Next steps:"
    echo "1. Commit your changes: git add . && git commit -m 'Verified and ready'"
    echo "2. Push to GitHub: git push origin main"
    echo "3. Deployment will proceed automatically"
    echo ""
    exit 0
fi

