#!/bin/bash
# Complete deployment script for Employee Suite

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🚀 Employee Suite - Production Deployment               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Step 1: Pre-deployment checks
echo -e "${BLUE}Step 1/5: Pre-deployment checks...${NC}"

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ Error: app.py not found!${NC}"
    exit 1
fi

# Check if Procfile exists
if [ ! -f "Procfile" ]; then
    echo -e "${RED}❌ Error: Procfile not found!${NC}"
    exit 1
fi

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Error: requirements.txt not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All required files present${NC}"

# Step 2: Generate secrets if needed
echo ""
echo -e "${BLUE}Step 2/5: Generating secrets...${NC}"

SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "")
CRON_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "")

if [ -z "$SECRET_KEY" ]; then
    echo -e "${YELLOW}⚠️  Could not generate SECRET_KEY automatically${NC}"
else
    echo -e "${GREEN}✅ Generated SECRET_KEY (save this!):${NC}"
    echo -e "${YELLOW}$SECRET_KEY${NC}"
fi

if [ -z "$CRON_SECRET" ]; then
    echo -e "${YELLOW}⚠️  Could not generate CRON_SECRET automatically${NC}"
else
    echo -e "${GREEN}✅ Generated CRON_SECRET (save this!):${NC}"
    echo -e "${YELLOW}$CRON_SECRET${NC}"
fi

# Step 3: Git status and commit
echo ""
echo -e "${BLUE}Step 3/5: Checking Git status...${NC}"

if [ ! -d ".git" ]; then
    echo -e "${YELLOW}⚠️  Not a git repository. Initializing...${NC}"
    git init
    git add .
    git commit -m "Initial commit - Production ready"
    echo -e "${GREEN}✅ Git repository initialized${NC}"
else
    # Check for changes
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "${YELLOW}⚠️  Uncommitted changes detected${NC}"
        echo "Files to commit:"
        git status --short
        
        read -p "Commit these changes? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git add -A
            git commit -m "Deploy: Production update $(date +%Y-%m-%d)"
            echo -e "${GREEN}✅ Changes committed${NC}"
        else
            echo -e "${YELLOW}⚠️  Skipping commit${NC}"
        fi
    else
        echo -e "${GREEN}✅ No uncommitted changes${NC}"
    fi
fi

# Step 4: Check remote
echo ""
echo -e "${BLUE}Step 4/5: Checking Git remote...${NC}"

if git remote | grep -q "origin"; then
    REMOTE_URL=$(git remote get-url origin)
    echo -e "${GREEN}✅ Remote configured: $REMOTE_URL${NC}"
    
    # Check if we need to push
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "")
    
    if [ -z "$REMOTE" ]; then
        echo -e "${YELLOW}⚠️  No upstream branch set${NC}"
        echo -e "${YELLOW}   Run: git push -u origin main${NC}"
    elif [ "$LOCAL" != "$REMOTE" ]; then
        echo -e "${YELLOW}⚠️  Local branch is ahead of remote${NC}"
        read -p "Push to remote now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git push origin main || git push origin master
            echo -e "${GREEN}✅ Pushed to remote${NC}"
        else
            echo -e "${YELLOW}⚠️  Skipping push${NC}"
        fi
    else
        echo -e "${GREEN}✅ Local and remote are in sync${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  No remote configured${NC}"
    echo ""
    echo "To set up remote:"
    echo "  1. Create a repo on GitHub"
    echo "  2. Run: git remote add origin <your-repo-url>"
    echo "  3. Run: git push -u origin main"
fi

# Step 5: Deployment instructions
echo ""
echo -e "${BLUE}Step 5/5: Deployment instructions...${NC}"
echo ""
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}📋 DEPLOYMENT CHECKLIST${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${GREEN}1. Environment Variables (REQUIRED in Render):${NC}"
echo ""
echo "   SECRET_KEY=$SECRET_KEY"
echo "   CRON_SECRET=$CRON_SECRET"
echo "   SHOPIFY_API_KEY=<from-partners-dashboard>"
echo "   SHOPIFY_API_SECRET=<from-partners-dashboard>"
echo "   SHOPIFY_REDIRECT_URI=https://your-app.onrender.com/oauth/callback"
echo "   APP_DOMAIN=your-app.onrender.com"
echo ""

echo -e "${GREEN}2. Deploy to Render:${NC}"
echo ""
echo "   Option A - Auto Deploy (if connected to GitHub):"
echo "   → Push to GitHub: git push origin main"
echo "   → Render will auto-deploy"
echo ""
echo "   Option B - Manual Deploy:"
echo "   → Go to: https://dashboard.render.com"
echo "   → Select your service"
echo "   → Click 'Manual Deploy' → 'Deploy latest commit'"
echo ""

echo -e "${GREEN}3. Verify Deployment:${NC}"
echo ""
echo "   → Check health: curl https://your-app.onrender.com/health"
echo "   → Should return: {\"status\":\"healthy\"...}"
echo ""

echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✅ Deployment preparation complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Set environment variables in Render dashboard"
echo "  2. Push to GitHub (if auto-deploy) or manually deploy"
echo "  3. Verify app is running"
echo ""










