#!/bin/bash
# Check deployment status and environment variables

echo "🔍 Checking Deployment Status..."
echo ""

# Check if app is live
echo "1. Checking if app is live..."
HEALTH=$(curl -s https://employeesuite-production.onrender.com/health)
if [ $? -eq 0 ]; then
    echo "✅ App is live and responding"
    echo "   Response: $(echo $HEALTH | head -c 100)..."
else
    echo "❌ App is not responding"
fi
echo ""

# Check Shopify settings page
echo "2. Checking Shopify settings page..."
SHOPIFY_PAGE=$(curl -s https://employeesuite-production.onrender.com/settings/shopify)
if echo "$SHOPIFY_PAGE" | grep -qi "configuration error"; then
    echo "❌ Configuration Error detected - Environment variables NOT set in Render"
elif echo "$SHOPIFY_PAGE" | grep -qi "connect.*shopify"; then
    echo "✅ Shopify settings page loads correctly"
else
    echo "⚠️  Could not determine status"
fi
echo ""

# Check git status
echo "3. Checking git status..."
echo "   Latest commit: $(git log -1 --oneline)"
echo "   Remote: $(git remote get-url origin)"
echo ""

# Check local .env
echo "4. Checking local .env file..."
if [ -f .env ]; then
    if grep -q "SHOPIFY_API_KEY=" .env; then
        echo "✅ Local .env has Shopify credentials"
    else
        echo "⚠️  Local .env exists but credentials may be different"
    fi
else
    echo "❌ No .env file found locally"
fi
echo ""

echo "════════════════════════════════════════════════════════"
echo "📋 NEXT STEPS:"
echo "════════════════════════════════════════════════════════"
echo ""
echo "If you see 'Configuration Error' on the deployed app:"
echo "  1. Go to: https://dashboard.render.com"
echo "  2. Find your service: EmployeeSuite-Production"
echo "  3. Click 'Environment' tab"
echo "  4. Add these variables:"
echo "     SHOPIFY_API_KEY=<your-api-key-from-partners-dashboard>"
echo "     SHOPIFY_API_SECRET=<your-api-secret-from-partners-dashboard>"
echo "     SHOPIFY_REDIRECT_URI=https://employeesuite-production.onrender.com/auth/callback"
echo "  5. Click 'Save Changes'"
echo "  6. Render will auto-redeploy"
echo ""


