#!/bin/bash
# Complete Verification System - Runs ALL checks before deployment

echo "🔍 COMPLETE PRE-DEPLOYMENT VERIFICATION"
echo "========================================"
echo ""
echo "This will run ALL verification checks:"
echo "  1. File verification"
echo "  2. Code syntax checks"
echo "  3. Configuration verification"
echo "  4. Functionality tests"
echo "  5. Security checks"
echo ""
echo "Deployment will ONLY proceed if ALL checks pass."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TOTAL_PASSED=0
TOTAL_FAILED=0

# Step 1: Pre-deployment verification
echo -e "${BLUE}STEP 1: Pre-Deployment Verification${NC}"
echo "----------------------------------------"
if ./pre_deploy_verification.sh; then
    echo -e "${GREEN}✅ Pre-deployment checks passed${NC}"
    TOTAL_PASSED=$((TOTAL_PASSED + 1))
else
    echo -e "${RED}❌ Pre-deployment checks failed${NC}"
    TOTAL_FAILED=$((TOTAL_FAILED + 1))
    echo ""
    echo "Deployment blocked. Fix issues and try again."
    exit 1
fi

echo ""
echo -e "${BLUE}STEP 2: Functionality Verification${NC}"
echo "----------------------------------------"
if python3 verify_app_functionality.py; then
    echo -e "${GREEN}✅ Functionality tests passed${NC}"
    TOTAL_PASSED=$((TOTAL_PASSED + 1))
else
    echo -e "${RED}❌ Functionality tests failed${NC}"
    TOTAL_FAILED=$((TOTAL_FAILED + 1))
    echo ""
    echo "Deployment blocked. Fix functionality issues and try again."
    exit 1
fi

echo ""
echo "========================================"
echo -e "${BLUE}📊 FINAL VERIFICATION SUMMARY${NC}"
echo "========================================"
echo -e "${GREEN}✅ Passed: $TOTAL_PASSED/2${NC}"
echo -e "${RED}❌ Failed: $TOTAL_FAILED/2${NC}"
echo ""

if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL VERIFICATIONS PASSED!${NC}"
    echo ""
    echo "Your app is verified and ready for deployment."
    echo ""
    echo "To deploy safely, run:"
    echo "  ./deploy_with_verification.sh"
    echo ""
    exit 0
else
    echo -e "${RED}🚫 DEPLOYMENT BLOCKED${NC}"
    echo ""
    echo "Please fix all issues before deploying."
    exit 1
fi

