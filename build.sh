#!/bin/bash
# Build script for Render deployment - OPTIMIZED to reduce build time/minutes
# This script installs dependencies efficiently to minimize build minutes

set -e

echo "🔧 Installing dependencies (optimized build)..."

# Upgrade pip (only if needed - cached on Render)
python3 -m pip install --upgrade --quiet pip setuptools wheel

# Install requirements with pip cache (faster, uses fewer minutes)
# --no-cache-dir disabled to allow Render's cache to speed things up
python3 -m pip install --quiet -r requirements.txt

echo "✅ Dependencies installed successfully"
