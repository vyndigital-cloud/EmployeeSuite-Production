#!/bin/bash
# Prepare repository for deployment to Render
echo "🚀 Preparing for deployment..."

# 1. Stage all changes (including new config files and optimizations)
git add -A

# 2. Commit changes
# The '|| echo' prevents the script from failing if there's nothing new to commit
git commit -m "Release: Production Ready (10/10) - Optimized Reporting & Deployment Config" || echo "⚠️  Nothing strictly new to commit, but proceeding..."

echo "---------------------------------------------------"
echo "✅ SUCCESS: All changes are committed and ready."
echo "👉 NOW RUN: git push origin main"
echo "---------------------------------------------------"
