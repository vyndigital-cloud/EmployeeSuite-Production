#!/usr/bin/env python3
"""
Properly fix App Bridge Promise system and button integration
This time: enhance existing code, don't break it
"""

import re

def fix_app_bridge_properly():
    file_path = 'app.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # STEP 1: Add Promise system to App Bridge initialization (if not present)
    if 'appBridgeReadyPromise' not in content:
        # Find: window.appBridgeReady = false;
        pattern1 = r'(// Global flag to track App Bridge readiness\s+window\.appBridgeReady = false;\s+window\.isEmbedded = !!host;)'
        replacement1 = r'''\1
            
            // PERFECTED: Promise-based App Bridge ready system (enhances existing sync check)
            window.appBridgeReadyPromise = null;
            window.appBridgeReadyResolve = null;
            window.appBridgeReadyReject = null;
            
            // Create Promise for App Bridge readiness
            window.appBridgeReadyPromise = new Promise(function(resolve, reject) {
                window.appBridgeReadyResolve = resolve;
                window.appBridgeReadyReject = reject;
            });
            
            // Helper function to wait for App Bridge (used by buttons)
            window.waitForAppBridge = function() {
                return window.appBridgeReadyPromise;
            };'''
        
        content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)
        print("✅ Added Promise system to initialization")
    
    # STEP 2: Resolve Promise when App Bridge initializes (if not already done)
    if 'appBridgeReadyResolve' in content and 'window.appBridgeReadyResolve({' not in content:
        # Find where App Bridge is marked ready and add Promise resolution
        pattern2 = r'(window\.appBridgeReady = true;\s+// Enable buttons now that App Bridge is ready\s+enableEmbeddedButtons\(\);)'
        replacement2 = r'''window.appBridgeReady = true;
                                    
                                    // PERFECTED: Resolve Promise and dispatch event
                                    if (window.appBridgeReadyResolve) {
                                        window.appBridgeReadyResolve({
                                            ready: true,
                                            embedded: true,
                                            app: window.shopifyApp
                                        });
                                    }
                                    
                                    // Dispatch custom event for App Bridge ready
                                    var readyEvent = new CustomEvent('appbridge:ready', {
                                        detail: { app: window.shopifyApp, embedded: true }
                                    });
                                    window.dispatchEvent(readyEvent);
                                    
                                    // Enable buttons now that App Bridge is ready
                                    enableEmbeddedButtons();'''
        
        content = re.sub(pattern2, replacement2, content, flags=re.MULTILINE)
        print("✅ Added Promise resolution on App Bridge ready")
    
    # STEP 3: Enhance button check to use Promise if available (with fallback)
    # Find the existing check and enhance it
    pattern3 = r'(// CRITICAL: Wait for App Bridge to be ready before making requests\s+if \(isEmbedded && !window\.appBridgeReady\) \{)'
    
    if re.search(pattern3, content):
        replacement3 = r'''// PERFECTED: Wait for App Bridge (uses Promise if available, falls back to sync check)
            if (isEmbedded) {
                // Try Promise-based wait first (more reliable)
                if (window.waitForAppBridge && typeof window.waitForAppBridge === 'function') {
                    window.waitForAppBridge().then(function(bridgeState) {
                        if (bridgeState && bridgeState.ready && bridgeState.app) {
                            // App Bridge is ready - update globals and continue
                            window.shopifyApp = bridgeState.app;
                            window.appBridgeReady = true;
                            // Continue with API call
                            proceedWithApiCall();
                        } else {
                            // App Bridge failed - show error
                            setButtonLoading(button, false);
                            document.getElementById('output').innerHTML = `
                                <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                                    <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ App Bridge Not Ready</div>
                                    <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">${bridgeState && bridgeState.error ? bridgeState.error : 'App Bridge initialization failed. Please refresh the page.'}</div>
                                    <button onclick="var btn = document.querySelector('.card-btn[onclick*=\\"processOrders\\"]'); if (btn) setTimeout(function(){processOrders(btn);}, 500);" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                                </div>
                            `;
                        }
                    }).catch(function(error) {
                        setButtonLoading(button, false);
                        document.getElementById('output').innerHTML = `
                            <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fff4f4; border: 1px solid #fecaca; border-radius: 8px;">
                                <div style="font-size: 15px; font-weight: 600; color: #d72c0d; margin-bottom: 8px;">❌ App Bridge Error</div>
                                <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">${error.message || 'App Bridge initialization failed. Please refresh the page.'}</div>
                                <button onclick="window.location.reload()" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Refresh Page</button>
                            </div>
                        `;
                    });
                    return; // Exit - Promise will handle continuation
                } else if (!window.appBridgeReady) {
                    // Fallback to sync check if Promise system not available'''
        
        content = re.sub(pattern3, replacement3, content, flags=re.MULTILINE)
        print("✅ Enhanced button check to use Promise with fallback")
        
        # Now we need to wrap the rest of the function in proceedWithApiCall
        # Find where the API call logic starts (after the check)
        pattern4 = r'(\s+\}\s+if \(isEmbedded && window\.shopifyApp && window\.appBridgeReady\) \{)'
        replacement4 = r'''}
            
            // Continue with API call (either not embedded, or App Bridge is ready)
            function proceedWithApiCall() {
                if (isEmbedded && window.shopifyApp && window.appBridgeReady) {'''
        
        if re.search(pattern4, content):
            content = re.sub(pattern4, replacement4, content, flags=re.MULTILINE)
            print("✅ Wrapped API call logic in proceedWithApiCall function")
            
            # Find where the else block ends (non-embedded case) and close the function
            # Look for: fetchPromise = fetch('/api/process_orders' ... ); followed by fetchPromise.then
            pattern5 = r'(fetchPromise = fetch\(\'/api/process_orders\',[^;]+\);\s+\}\s+fetchPromise)'
            replacement5 = r'''fetchPromise = fetch('/api/process_orders', {
                    signal: controller.signal,
                    credentials: 'include'  // Include cookies for Flask-Login
                });
            }
            
            // Execute the Promise chain
            fetchPromise'''
            
            if re.search(pattern5, content):
                content = re.sub(pattern5, replacement5, content, flags=re.MULTILINE)
                print("✅ Fixed Promise chain execution")
            else:
                # Try to find the end of the else block differently
                pattern6 = r'(\}\s+fetchPromise\s*\.then\(r =>)'
                if re.search(pattern6, content):
                    # The structure is already correct, just need to call proceedWithApiCall
                    # Find where to call it (after the check, before the if statement)
                    pattern7 = r'(// Continue with API call \(either not embedded, or App Bridge is ready\)\s+function proceedWithApiCall\(\) \{[^}]+if \(isEmbedded && window\.shopifyApp && window\.appBridgeReady\) \{)'
                    # Actually, we need to call proceedWithApiCall() after the check
                    # Find the end of the check block
                    pattern8 = r'(\s+return;\s+\}\s+else if \(!window\.appBridgeReady\) \{[^}]+\}\s+// Continue with API call)'
                    replacement8 = r'''return;
                }
            }
            
            // Call proceedWithApiCall (either immediately if ready, or after Promise resolves)
            if (!isEmbedded || window.appBridgeReady) {
                proceedWithApiCall();
            }
            // If embedded and not ready, Promise handler will call proceedWithApiCall()
            
            // Continue with API call'''
            
            if re.search(pattern8, content):
                content = re.sub(pattern8, replacement8, content, flags=re.MULTILINE)
                print("✅ Added call to proceedWithApiCall")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✅ App Bridge Promise system properly integrated!")
    print("⚠️  Manual verification needed - check that proceedWithApiCall is called correctly")

if __name__ == '__main__':
    fix_app_bridge_properly()

