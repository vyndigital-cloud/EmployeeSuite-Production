#!/bin/bash
# Quick script to verify everything is ready for Render auto-deployment

echo "🔍 Verifying Render Auto-Deployment Setup..."
echo ""

# Check git remote
echo "📦 GitHub Remote:"
git remote get-url origin 2>/dev/null || echo "❌ No remote configured"
echo ""

# Check current branch
echo "🌿 Current Branch:"
git branch --show-current
echo ""

# Check if code is pushed
echo "📤 Git Status:"
git status -sb
echo ""

# Check latest commit
echo "📝 Latest Commit:"
git log --oneline -1
echo ""

# Check required files
echo "📄 Required Files for Render:"
FILES=("Procfile" "requirements.txt" "runtime.txt" "app.py")
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (MISSING)"
    fi
done
echo ""

# Final status
if git status -sb | grep -q "ahead"; then
    echo "⚠️  WARNING: You have unpushed commits!"
    echo "   Run: git push origin main"
else
    echo "✅ All commits are pushed to GitHub"
fi

echo ""
echo "🎯 Next Steps:"
echo "1. Go to Render dashboard: https://dashboard.render.com"
echo "2. Select your web service"
echo "3. Settings → Build & Deploy"
echo "4. Verify Auto-Deploy is set to 'Yes'"
echo "5. Verify Branch is set to 'main'"
echo "6. Save changes"
echo ""
echo "📚 Full guide: See RENDER_AUTO_DEPLOY_FIX.md"

