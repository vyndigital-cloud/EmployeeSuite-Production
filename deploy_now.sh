#!/bin/bash

# Deploy Employee Suite to Production
# This script deploys your fully Shopify-compliant app

set -e

echo "🚀 Deploying Employee Suite to Production..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📦 Initializing Git repository..."
    git init
    git add .
    git commit -m "Initial commit - Shopify compliant app"
else
    echo "📝 Staging changes..."
    git add .
    git commit -m "Deploy: Full Shopify compliance implementation" || echo "No changes to commit"
fi

# Check if Render remote exists
if ! git remote get-url render >/dev/null 2>&1; then
    echo "🔗 Adding Render remote..."
    echo "Please add your Render Git URL:"
    echo "git remote add render <YOUR_RENDER_GIT_URL>"
    echo "Then run this script again."
    exit 1
fi

echo "📤 Pushing to Render..."
git push render main

echo "✅ Deployment initiated!"
echo ""
echo "📋 Next Steps:"
echo "1. Monitor deployment at: https://dashboard.render.com"
echo "2. Update environment variables in Render dashboard:"
echo "   - SHOPIFY_API_KEY"
echo "   - SHOPIFY_API_SECRET"
echo "   - SENTRY_DSN (optional)"
echo "3. Update webhook URLs in Shopify Partners"
echo "4. Test the deployed app"
echo ""
echo "🎉 Your Shopify-compliant app is being deployed!"
