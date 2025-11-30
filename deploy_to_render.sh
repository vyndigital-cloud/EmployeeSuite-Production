#!/bin/bash
# deploy_to_render.sh - One-command deployment to Render.com

set -e  # Exit on any error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🚀 Employee Suite - Auto Deploy to Render.com            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check if we're in the right directory
echo -e "${BLUE}Step 1/6: Checking directory...${NC}"
if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ Error: app.py not found!${NC}"
    echo "Please run this script from the 1EmployeeSuite directory"
    exit 1
fi
echo -e "${GREEN}✅ Found app.py${NC}"
echo ""

# Step 2: Check Python version
echo -e "${BLUE}Step 2/6: Checking Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi
echo ""

# Step 3: Initialize Git repo
echo -e "${BLUE}Step 3/6: Setting up Git...${NC}"
if [ ! -d ".git" ]; then
    git init
    echo -e "${GREEN}✅ Git initialized${NC}"
else
    echo -e "${YELLOW}⚠️  Git already initialized${NC}"
fi
echo ""

# Step 4: Add all files
echo -e "${BLUE}Step 4/6: Staging files...${NC}"
git add .
echo -e "${GREEN}✅ Files staged${NC}"
echo ""

# Step 5: Commit
echo -e "${BLUE}Step 5/6: Creating commit...${NC}"
git commit -m "Production-ready Employee Suite for Render deployment" 2>/dev/null || echo -e "${YELLOW}⚠️  No changes to commit${NC}"
echo -e "${GREEN}✅ Committed${NC}"
echo ""

# Step 6: Instructions for GitHub
echo -e "${BLUE}Step 6/6: GitHub Setup${NC}"
echo ""
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}IMPORTANT: Complete these manual steps now:${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo ""
echo "1️⃣  Go to: ${GREEN}https://github.com/new${NC}"
echo ""
echo "2️⃣  Create a repo named: ${GREEN}1EmployeeSuite${NC}"
echo "    (Make it Public or Private - your choice)"
echo ""
echo "3️⃣  Copy the repo URL (it will look like):"
echo "    ${GREEN}https://github.com/YOUR_USERNAME/1EmployeeSuite.git${NC}"
echo ""
echo "4️⃣  Run these commands:"
echo ""
echo -e "${GREEN}git remote add origin https://github.com/YOUR_USERNAME/1EmployeeSuite.git${NC}"
echo -e "${GREEN}git branch -M main${NC}"
echo -e "${GREEN}git push -u origin main${NC}"
echo ""
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo ""
echo "5️⃣  After pushing, go to: ${GREEN}https://render.com${NC}"
echo ""
echo "6️⃣  Click: ${GREEN}New + → Web Service${NC}"
echo ""
echo "7️⃣  Connect your GitHub and select: ${GREEN}1EmployeeSuite${NC}"
echo ""
echo "8️⃣  Render will auto-detect settings. Just click: ${GREEN}Create Web Service${NC}"
echo ""
echo "9️⃣  Wait 2-3 minutes for build to complete"
echo ""
echo "🔟 Visit your live app at: ${GREEN}https://your-app-name.onrender.com${NC}"
echo ""
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✅ Local setup complete!${NC}"
echo -e "${GREEN}✅ Ready to push to GitHub and deploy to Render${NC}"
echo ""
echo "Need help? Check RENDER_DEPLOYMENT.md for detailed instructions"
echo ""
