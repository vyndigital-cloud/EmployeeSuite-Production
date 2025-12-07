#!/bin/bash
# Build script for Render deployment
# This script installs dependencies without hash checking to avoid deployment issues

set -e

echo "🔧 Installing dependencies..."

# Upgrade pip first
python3 -m pip install --upgrade pip setuptools wheel

# Install requirements without hash checking
python3 -m pip install --no-require-hashes -r requirements.txt

echo "✅ Dependencies installed successfully"
