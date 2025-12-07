#!/bin/bash
# Build script for Render deployment
# This script installs dependencies without hash checking to avoid deployment issues

set -e

echo "🔧 Installing dependencies..."

# Upgrade pip first
python3 -m pip install --upgrade pip setuptools wheel

# Install requirements - pip will skip hash checking if hashes aren't in file
python3 -m pip install -r requirements.txt

echo "✅ Dependencies installed successfully"
