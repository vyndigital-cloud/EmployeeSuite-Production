#!/bin/bash
# Deploy shopify.app.toml compliance webhooks to Shopify

set -e

echo "🚀 Deploying Shopify Compliance Webhooks"
echo "=========================================="
echo ""

# Check if Shopify CLI is installed
if ! command -v shopify &> /dev/null; then
    echo "❌ Shopify CLI not found. Installing..."
    echo ""
    echo "Installing via npm..."
    npm install -g @shopify/cli @shopify/theme
    
    if ! command -v shopify &> /dev/null; then
        echo "❌ Installation failed. Please install manually:"
        echo "   npm install -g @shopify/cli @shopify/theme"
        exit 1
    fi
    echo "✅ Shopify CLI installed successfully!"
    echo ""
fi

echo "✅ Shopify CLI found: $(shopify version)"
echo ""

# Navigate to project directory
cd "$(dirname "$0")"
echo "📁 Working directory: $(pwd)"
echo ""

# Check if shopify.app.toml exists
if [ ! -f "shopify.app.toml" ]; then
    echo "❌ shopify.app.toml not found!"
    exit 1
fi

echo "✅ Found shopify.app.toml"
echo ""
echo "🔍 Configuration:"
cat shopify.app.toml | grep -E "(compliance_topics|uri)" | sed 's/^/   /'
echo ""

# Check if already linked to an app
echo "🔗 Checking app link status..."
echo ""

# Deploy
echo "📤 Deploying webhook configuration..."
echo ""
shopify app deploy --no-release

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Wait 2-3 minutes for Shopify to process"
echo "   2. Go to Partners Dashboard → Distribution"
echo "   3. Click 'Run' to re-run automated checks"
echo "   4. Verify webhook compliance errors are resolved"
echo ""
