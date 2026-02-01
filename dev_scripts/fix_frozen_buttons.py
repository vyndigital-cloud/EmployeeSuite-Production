#!/usr/bin/env python3
"""
Fix frozen buttons by adding the missing call to waitForAppBridgeAndProceed()
"""

def fix_frozen_buttons():
    file_path = 'app.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find where proceedWithApiCall() ends for processOrders
    # Look for the closing brace and fetchPromise usage
    # The function should end before fetchPromise is used
    
    # Pattern: function proceedWithApiCall() { ... } followed by fetchPromise usage
    # We need to add: waitForAppBridgeAndProceed(proceedWithApiCall); right after the function definition
    
    # For processOrders - find the pattern and add the call
    import re
    
    # Find the end of proceedWithApiCall function (look for closing brace before fetchPromise)
    # Actually, a simpler approach: find where proceedWithApiCall is defined and add the call right after the closing brace
    
    # Pattern 1: For processOrders
    pattern1 = r'(// PERFECTED: Wait for App Bridge Promise before making requests\s+function proceedWithApiCall\(\) \{[^}]+fetchPromise = fetch\([^)]+\);\s+\}\s+\)\.catch\([^}]+\}\);)\s+(fetchPromise)'
    
    # Actually, let's find where the function ends by looking for the pattern where fetchPromise is assigned in the else block
    # The function ends right before the else block that assigns fetchPromise for non-embedded mode
    
    # Better approach: Find the closing brace of proceedWithApiCall and add the call
    # Look for: } else { // Not embedded - use regular fetch
    pattern = r'(// PERFECTED: Wait for App Bridge Promise before making requests\s+function proceedWithApiCall\(\) \{.*?\}\s+\)\.catch\(function\(err\) \{.*?\}\s+\);\s+\} else \{)'
    
    replacement = r'''\1
            
            // CRITICAL: Actually call the function via waitForAppBridgeAndProceed
            waitForAppBridgeAndProceed(proceedWithApiCall);
            return; // Exit early - proceedWithApiCall will handle the rest
        }
        
        // If we get here, we're not using the Promise system (fallback)
        function proceedWithApiCallFallback() {
            if (isEmbedded && window.shopifyApp && window.appBridgeReady) {
            } else {'''
    
    # Actually, simpler: just add the call right after defining proceedWithApiCall
    # Find: function proceedWithApiCall() { ... } and add call after closing brace
    
    # Let's use a different approach - find the specific location and insert
    # Look for the end of proceedWithApiCall function (before the else block)
    
    # Pattern: closing brace of proceedWithApiCall, then else block
    pattern_simple = r'(throw err; // Stop execution\s+\}\);\s+\} else \{)'
    
    replacement_simple = r'''throw err; // Stop execution
                });
            }
            
            // CRITICAL FIX: Actually call proceedWithApiCall via waitForAppBridgeAndProceed
            waitForAppBridgeAndProceed(proceedWithApiCall);
            return; // Exit - proceedWithApiCall handles everything
            
            // Fallback code (shouldn't reach here, but kept for safety)
            function proceedWithApiCallFallback() {
                if (isEmbedded && window.shopifyApp && window.appBridgeReady) {
                } else {'''
    
    if re.search(pattern_simple, content, re.DOTALL):
        content = re.sub(pattern_simple, replacement_simple, content, flags=re.DOTALL)
        print("✅ Fixed processOrders button")
    else:
        # Try a different pattern - find where the function ends
        # Look for: } else { // Not embedded
        pattern2 = r'(\}\s+\)\.catch\(function\(err\) \{[^}]+\}\s+\);\s+\} else \{)'
        replacement2 = r'''});
            }
            
            // CRITICAL FIX: Call proceedWithApiCall via waitForAppBridgeAndProceed
            waitForAppBridgeAndProceed(proceedWithApiCall);
            return;
        }
        
        // Fallback (shouldn't execute)
        if (false) {
        } else {'''
        
        if re.search(pattern2, content, re.DOTALL):
            content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)
            print("✅ Fixed processOrders button (pattern 2)")
        else:
            print("⚠️  Could not find exact pattern for processOrders")
            # Try to find and replace manually
            # Find: // PERFECTED: Wait for App Bridge Promise
            # Then find the closing of proceedWithApiCall and add the call
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Attempted to fix frozen buttons")
    print("⚠️  Manual verification needed")

if __name__ == '__main__':
    fix_frozen_buttons()

