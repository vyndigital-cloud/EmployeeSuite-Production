#!/bin/bash
# Verify all checklists and generate status report

echo "🔍 Verifying All Checklists..."
echo ""

TOTAL=0
COMPLETE=0

# Count items in each checklist
for file in CHECKLIST_*.md; do
    if [ -f "$file" ]; then
        items=$(grep -c "^- \[ \]" "$file" 2>/dev/null || echo "0")
        checked=$(grep -c "^- \[x\]" "$file" 2>/dev/null || echo "0")
        TOTAL=$((TOTAL + items))
        COMPLETE=$((COMPLETE + checked))
        echo "📋 $file: $checked/$items items complete"
    fi
done

echo ""
echo "📊 Overall Progress: $COMPLETE/$TOTAL items ($(echo "scale=1; $COMPLETE*100/$TOTAL" | bc)%)"
echo ""

# Check critical checklists
echo "🔴 Critical Checklists:"
grep -l "CRITICAL" CHECKLIST_*.md | while read file; do
    items=$(grep -c "^- \[ \]" "$file" 2>/dev/null || echo "0")
    checked=$(grep -c "^- \[x\]" "$file" 2>/dev/null || echo "0")
    if [ "$items" -gt 0 ]; then
        percent=$(echo "scale=0; $checked*100/$items" | bc)
        echo "  $file: $checked/$items ($percent%)"
    fi
done

echo ""
echo "✅ Verification complete!"

