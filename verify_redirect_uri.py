#!/usr/bin/env python3
"""
Verify OAuth Redirect URI Configuration
This script helps diagnose redirect_uri whitelist errors.
"""

import os
from urllib.parse import quote

def verify_redirect_uri():
    """Check redirect URI configuration"""
    print("=" * 60)
    print("OAuth Redirect URI Verification")
    print("=" * 60)
    print()
    
    # Get redirect URI from environment or default
    redirect_uri = os.getenv('SHOPIFY_REDIRECT_URI', 'https://employeesuite-production.onrender.com/auth/callback')
    
    print(f"📋 Current Redirect URI Configuration:")
    print(f"   {redirect_uri}")
    print()
    
    # Check for common issues
    issues = []
    warnings = []
    
    # Check protocol
    if not redirect_uri.startswith('https://'):
        issues.append("❌ Must use https:// (not http://)")
    else:
        print("✅ Using https:// protocol")
    
    # Check trailing slash
    if redirect_uri.endswith('/'):
        issues.append("❌ Has trailing slash (remove it)")
    else:
        print("✅ No trailing slash")
    
    # Check path
    if '/auth/callback' not in redirect_uri:
        warnings.append("⚠️  Path should be /auth/callback")
    else:
        print("✅ Path is /auth/callback")
    
    # Check for query parameters
    if '?' in redirect_uri:
        issues.append("❌ Contains query parameters (remove them)")
    else:
        print("✅ No query parameters")
    
    # Show URL-encoded version (for reference)
    encoded = quote(redirect_uri, safe='')
    print()
    print(f"📝 URL-encoded version (for query string):")
    print(f"   {encoded}")
    print()
    
    # Expected value
    expected = 'https://employeesuite-production.onrender.com/auth/callback'
    print(f"✅ Expected value (default):")
    print(f"   {expected}")
    print()
    
    if redirect_uri == expected:
        print("✅ Redirect URI matches expected default value")
    else:
        print("⚠️  Redirect URI differs from default")
        print("   Make sure this is also added to Partners Dashboard")
    
    print()
    print("=" * 60)
    
    if issues:
        print("🚨 ISSUES FOUND:")
        for issue in issues:
            print(f"   {issue}")
        print()
    
    if warnings:
        print("⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")
        print()
    
    if not issues and not warnings:
        print("✅ No issues found with redirect URI format")
        print()
        print("📋 Next Steps:")
        print("   1. Go to Shopify Partners Dashboard")
        print("   2. Navigate to: Apps → Your App → App Setup")
        print("   3. Scroll to 'Allowed redirection URLs'")
        print(f"   4. Add this URL: {redirect_uri}")
        print("   5. Save and wait 1-2 minutes")
        print("   6. Try OAuth again")
    
    print("=" * 60)

if __name__ == '__main__':
    verify_redirect_uri()

