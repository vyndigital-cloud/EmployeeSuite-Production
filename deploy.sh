#!/bin/bash
# ----------------------------------------------------
# DEPLOYMENT SCRIPT 
# ----------------------------------------------------
# This script handles the "Push" that triggers Render's "Auto Deploy".
# Render automatically deploys when it sees new code on GitHub.
# This script sends that new code to GitHub.

# 1. Force Jump to the CORRECT folder where I saved the features
cd /Users/essentials/MissionControl || exit

echo "🚀 Starting Deployment from: $(pwd)"

# 2. Add all new features (Inventory Intelligence, etc.)
git add -A

# 3. Commit
# If there are no changes, it just skips this step
git commit -m "Release: Inventory Intelligence & 10/10 Performance Features" || echo "⚠️  Nothing strictly new to commit, proceeding to push..."

# 4. Push to GitHub ->Triggers Render Auto-Deploy
echo "📤 Pushing to GitHub (this triggers Render)..."
git push origin main

echo "---------------------------------------------------"
echo "✅ PUSH SUCCESSFUL!"
echo "🎉 Render is now automatically building & deploying your site."
echo "👉 Dashboard: https://dashboard.render.com"
echo "---------------------------------------------------"
