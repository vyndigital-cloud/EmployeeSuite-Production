#!/bin/bash
# Static Analysis - Security-First Scan for EmployeeSuite
# Focuses on JWT/OAuth/Session critical paths

echo "🔍 Installing analysis tools..."
pip install -q mypy ruff

echo ""
echo "========================================"
echo "🛡️  SECURITY SCAN - Critical Paths"
echo "========================================"
echo ""

# Critical security files to analyze
CRITICAL_FILES=(
    "session_token_verification.py"
    "shopify_oauth.py"
    "app_factory.py"
    "auth.py"
    "shopify_routes.py"
)

echo "📋 Analyzing ${#CRITICAL_FILES[@]} critical security files..."
echo ""

# Run Ruff on critical files only (fast)
echo "🚀 [1/2] Ruff Security Scan..."
ruff check "${CRITICAL_FILES[@]}" --select S,B,F --output-format=concise

echo ""
echo "🔬 [2/2] Mypy Type Safety Check..."
mypy "${CRITICAL_FILES[@]}" --show-error-codes --pretty

echo ""
echo "========================================"
echo "✅ Analysis Complete"
echo "========================================"
echo ""
echo "To run full codebase scan (will be verbose):"
echo "  ruff check . --select ALL"
echo "  mypy . --strict"
echo ""
