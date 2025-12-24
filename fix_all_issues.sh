#!/bin/bash
# Auto-fix common issues across all checklists

echo "🔧 Auto-Fixing Issues..."
echo ""

# Fix technical issues
if [ -f "fix_technical_issues.sh" ]; then
    echo "1️⃣ Fixing technical issues..."
    ./fix_technical_issues.sh
fi

# Fix security issues
if [ -f "fix_security_issues.sh" ]; then
    echo "2️⃣ Fixing security issues..."
    ./fix_security_issues.sh
fi

# Fix billing issues
if [ -f "fix_billing_issues.sh" ]; then
    echo "3️⃣ Fixing billing issues..."
    ./fix_billing_issues.sh
fi

# Fix webhook issues
if [ -f "fix_webhook_issues.sh" ]; then
    echo "4️⃣ Fixing webhook issues..."
    ./fix_webhook_issues.sh
fi

echo ""
echo "✅ Auto-fix complete! Run verify_all_checklists.sh to check status."

