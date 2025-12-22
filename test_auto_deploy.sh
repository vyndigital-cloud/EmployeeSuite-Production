#!/bin/bash
# Test auto-deployment by making a small change and pushing

echo "🧪 Testing Auto-Deployment..."
echo ""

# Create a test commit
echo "# Auto-deploy test - $(date)" >> .auto_deploy_test.txt
git add .auto_deploy_test.txt
git commit -m "TEST: Auto-deploy verification $(date +%Y%m%d-%H%M%S)" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Test commit created"
    echo ""
    echo "📤 Pushing to GitHub..."
    git push origin main
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Push successful!"
        echo ""
        echo "🔍 Next Steps:"
        echo "1. Go to Render Dashboard: https://dashboard.render.com"
        echo "2. Click your web service"
        echo "3. Go to 'Events' tab"
        echo "4. You should see a new deployment starting within 10-30 seconds"
        echo ""
        echo "⏱️  Wait 2-3 minutes for deployment to complete"
        echo ""
        echo "🧹 Cleanup:"
        echo "   Run: git reset HEAD~1 && git restore .auto_deploy_test.txt"
    else
        echo "❌ Push failed. Check your git credentials."
    fi
else
    echo "⚠️  No changes to commit (this is OK if you just tested)"
fi

