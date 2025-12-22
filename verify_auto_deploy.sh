#!/bin/bash
# Comprehensive auto-deployment verification and setup

echo "🚀 Render Auto-Deployment Verification"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check 1: Git remote
echo -e "${BLUE}1. Checking GitHub Remote...${NC}"
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
if [ -n "$REMOTE_URL" ]; then
    echo -e "${GREEN}✅ Remote: $REMOTE_URL${NC}"
else
    echo -e "${RED}❌ No remote configured${NC}"
    exit 1
fi
echo ""

# Check 2: Current branch
echo -e "${BLUE}2. Checking Current Branch...${NC}"
BRANCH=$(git branch --show-current)
echo -e "${GREEN}✅ Branch: $BRANCH${NC}"
if [ "$BRANCH" != "main" ]; then
    echo -e "${YELLOW}⚠️  Warning: Not on 'main' branch. Auto-deploy should use 'main'${NC}"
fi
echo ""

# Check 3: Unpushed commits
echo -e "${BLUE}3. Checking for Unpushed Commits...${NC}"
UNPUSHED=$(git status -sb 2>/dev/null | grep -c "ahead" || echo "0")
if [ "$UNPUSHED" -gt 0 ] 2>/dev/null; then
    echo -e "${YELLOW}⚠️  You have unpushed commits!${NC}"
    echo "   Run: git push origin $BRANCH"
else
    echo -e "${GREEN}✅ All commits are pushed${NC}"
fi
echo ""

# Check 4: Required files
echo -e "${BLUE}4. Checking Required Files...${NC}"
FILES=("Procfile" "requirements.txt" "runtime.txt" "app.py")
ALL_OK=true
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}  ✅ $file${NC}"
    else
        echo -e "${RED}  ❌ $file (MISSING)${NC}"
        ALL_OK=false
    fi
done
echo ""

# Check 5: Latest commit
echo -e "${BLUE}5. Latest Commit:${NC}"
git log --oneline -1
echo ""

# Summary
echo "========================================"
echo -e "${BLUE}📊 Summary:${NC}"
echo ""

ISSUES=0
if [ "$ALL_OK" != true ]; then
    ISSUES=1
fi
if [ "$UNPUSHED" -gt 0 ] 2>/dev/null; then
    ISSUES=1
fi

if [ "$ISSUES" -eq 0 ]; then
    echo -e "${GREEN}✅ Code is ready for auto-deployment!${NC}"
    echo ""
    echo -e "${YELLOW}📋 Next Steps:${NC}"
    echo ""
    echo "1. Go to Render Dashboard:"
    echo "   https://dashboard.render.com"
    echo ""
    echo "2. Select your web service"
    echo ""
    echo "3. Go to: Settings → Build & Deploy"
    echo ""
    echo "4. Verify these settings:"
    echo "   - Auto-Deploy: ${GREEN}Yes${NC}"
    echo "   - Branch: ${GREEN}main${NC}"
    echo "   - GitHub Repo: ${GREEN}$REMOTE_URL${NC}"
    echo ""
    echo "5. Click ${GREEN}Save Changes${NC}"
    echo ""
    echo "6. Test auto-deploy:"
    echo "   Run: ./test_auto_deploy.sh"
else
    echo -e "${YELLOW}⚠️  Fix these issues first:${NC}"
    [ "$ALL_OK" != true ] && echo "   - Missing required files"
    [ "$UNPUSHED" -gt 0 ] 2>/dev/null && echo "   - Push your commits"
    echo ""
fi

echo "========================================"
