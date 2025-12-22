#!/bin/bash
# Enable Render auto-deployment via API

echo "🚀 Enabling Render Auto-Deployment..."
echo ""

# Check if RENDER_API_KEY is set
if [ -z "$RENDER_API_KEY" ]; then
    echo "⚠️  RENDER_API_KEY not set"
    echo ""
    echo "To enable auto-deploy programmatically, you need:"
    echo "1. Get your API key from: https://dashboard.render.com/account/api-keys"
    echo "2. Export it: export RENDER_API_KEY=your_key_here"
    echo "3. Run this script again"
    echo ""
    echo "OR manually enable in Render dashboard:"
    echo "1. Go to: https://dashboard.render.com"
    echo "2. Select your web service"
    echo "3. Settings → Build & Deploy"
    echo "4. Set Auto-Deploy: Yes"
    echo "5. Branch: main"
    echo "6. Save"
    exit 1
fi

# Get service ID (you'll need to provide this)
SERVICE_ID="${RENDER_SERVICE_ID}"

if [ -z "$SERVICE_ID" ]; then
    echo "⚠️  RENDER_SERVICE_ID not set"
    echo ""
    echo "To find your service ID:"
    echo "1. Go to Render dashboard → Your service"
    echo "2. The URL will be: https://dashboard.render.com/web/YOUR_SERVICE_ID"
    echo "3. Export it: export RENDER_SERVICE_ID=your_service_id"
    echo ""
    exit 1
fi

echo "✅ Using service ID: $SERVICE_ID"
echo ""

# Enable auto-deploy via API
RESPONSE=$(curl -s -X PATCH \
    -H "Authorization: Bearer $RENDER_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "autoDeploy": "yes",
        "branch": "main"
    }' \
    "https://api.render.com/v1/services/$SERVICE_ID")

if echo "$RESPONSE" | grep -q "autoDeploy"; then
    echo "✅ Auto-deploy enabled successfully!"
else
    echo "❌ Failed to enable auto-deploy"
    echo "Response: $RESPONSE"
    echo ""
    echo "Please enable manually in Render dashboard"
fi

