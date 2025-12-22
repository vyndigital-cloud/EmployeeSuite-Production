#!/bin/bash
# Safe Deployment Script - Only deploys after verification

echo "🚀 SAFE DEPLOYMENT SYSTEM"
echo "========================="
echo ""

# Run pre-deployment verification
echo "Step 1: Running pre-deployment verification..."
echo ""

if ./pre_deploy_verification.sh; then
    echo ""
    echo -e "\033[0;32m✅ Verification passed! Proceeding with deployment...\033[0m"
    echo ""
    
    # Check if we're in a git repo
    if [ ! -d ".git" ]; then
        echo "❌ Not a git repository. Cannot deploy."
        exit 1
    fi
    
    # Check if there are uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo "⚠️  You have uncommitted changes."
        echo ""
        echo "Options:"
        echo "1. Commit changes first: git add . && git commit -m 'Your message'"
        echo "2. Stash changes: git stash"
        echo "3. Review changes: git status"
        echo ""
        read -p "Do you want to commit all changes now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git add .
            read -p "Enter commit message: " commit_msg
            git commit -m "${commit_msg:-Verified and ready for deployment}"
        else
            echo "Deployment cancelled. Please commit or stash your changes."
            exit 1
        fi
    fi
    
    # Check current branch
    CURRENT_BRANCH=$(git branch --show-current)
    if [ "$CURRENT_BRANCH" != "main" ]; then
        echo "⚠️  You're not on 'main' branch (currently on: $CURRENT_BRANCH)"
        read -p "Deploy from this branch? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Deployment cancelled. Switch to main branch first."
            exit 1
        fi
    fi
    
    # Check if remote is configured
    if ! git remote get-url origin > /dev/null 2>&1; then
        echo "❌ No remote configured. Cannot push."
        exit 1
    fi
    
    # Show what will be deployed
    echo ""
    echo "📤 Deployment Summary:"
    echo "   Branch: $CURRENT_BRANCH"
    echo "   Remote: $(git remote get-url origin)"
    echo "   Latest commit: $(git log --oneline -1)"
    echo ""
    
    read -p "Proceed with deployment? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "🚀 Pushing to GitHub..."
        git push origin "$CURRENT_BRANCH"
        
        if [ $? -eq 0 ]; then
            echo ""
            echo -e "\033[0;32m✅ Deployment initiated successfully!\033[0m"
            echo ""
            echo "Your code has been pushed to GitHub."
            echo "If auto-deploy is enabled, Render will deploy automatically."
            echo ""
            echo "Monitor deployment:"
            echo "  https://dashboard.render.com"
            echo ""
        else
            echo ""
            echo -e "\033[0;31m❌ Push failed. Check your git credentials and try again.\033[0m"
            exit 1
        fi
    else
        echo "Deployment cancelled."
        exit 0
    fi
else
    echo ""
    echo -e "\033[0;31m❌ Verification failed! Deployment blocked.\033[0m"
    echo ""
    echo "Please fix all critical issues before deploying."
    echo "Run: ./pre_deploy_verification.sh"
    exit 1
fi

