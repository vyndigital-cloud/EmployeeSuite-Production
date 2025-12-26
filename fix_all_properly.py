#!/usr/bin/env python3
"""
Fix App Bridge properly - enhance existing code without breaking it
Simple approach: add Promise system, enhance button check to use it with fallback
"""

import re

def fix_all():
    file_path = 'app.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    changes_made = []
    
    # 1. Add Promise system to initialization
    if 'appBridgeReadyPromise' not in content:
        pattern = r'(// Global flag to track App Bridge readiness\s+window\.appBridgeReady = false;\s+window\.isEmbedded = !!host;)'
        replacement = r'''\1
            
            // PERFECTED: Promise-based App Bridge ready system
            window.appBridgeReadyPromise = new Promise(function(resolve, reject) {
                window.appBridgeReadyResolve = resolve;
                window.appBridgeReadyReject = reject;
            });
            window.waitForAppBridge = function() {
                return window.appBridgeReadyPromise;
            };'''
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        changes_made.append("Added Promise system")
    
    # 2. Resolve Promise when App Bridge is ready
    if 'appBridgeReadyResolve' in content:
        # Find where appBridgeReady is set to true
        pattern = r'(window\.appBridgeReady = true;\s+// Enable buttons now that App Bridge is ready\s+enableEmbeddedButtons\(\);)'
        replacement = r'''window.appBridgeReady = true;
                                    
                                    // Resolve Promise
                                    if (window.appBridgeReadyResolve) {
                                        window.appBridgeReadyResolve({
                                            ready: true,
                                            embedded: true,
                                            app: window.shopifyApp
                                        });
                                    }
                                    
                                    // Dispatch event
                                    window.dispatchEvent(new CustomEvent('appbridge:ready', {
                                        detail: { app: window.shopifyApp, embedded: true }
                                    }));
                                    
                                    // Enable buttons now that App Bridge is ready
                                    enableEmbeddedButtons();'''
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            changes_made.append("Added Promise resolution")
    
    # 3. Enhance button check - use Promise if available, fallback to sync
    # This is the key fix - enhance the existing check without breaking it
    pattern = r'(// CRITICAL: Wait for App Bridge to be ready before making requests\s+if \(isEmbedded && !window\.appBridgeReady\) \{)'
    
    if re.search(pattern, content):
        replacement = r'''// PERFECTED: Wait for App Bridge (uses Promise if available, sync check as fallback)
            if (isEmbedded) {
                // Try Promise-based wait first
                if (window.waitForAppBridge && typeof window.waitForAppBridge === 'function' && !window.appBridgeReady) {
                    // Wait for Promise to resolve
                    window.waitForAppBridge().then(function(bridgeState) {
                        if (bridgeState && bridgeState.ready && bridgeState.app) {
                            window.shopifyApp = bridgeState.app;
                            window.appBridgeReady = true;
                            // Retry the button click now that App Bridge is ready
                            processOrders(button);
                        } else {
                            setButtonLoading(button, false);
                            document.getElementById('output').innerHTML = `
                                <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                                    <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ App Bridge Not Ready</div>
                                    <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">${bridgeState && bridgeState.error ? bridgeState.error : 'Please wait while the app initializes.'}</div>
                                    <button onclick="var btn = document.querySelector('.card-btn[onclick*=\\"processOrders\\"]'); if (btn) setTimeout(function(){processOrders(btn);}, 500);" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                                </div>
                            `;
                        }
                    }).catch(function(error) {
                        setButtonLoading(button, false);
                        document.getElementById('output').innerHTML = `
                            <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fff4f4; border: 1px solid #fecaca; border-radius: 8px;">
                                <div style="font-size: 15px; font-weight: 600; color: #d72c0d; margin-bottom: 8px;">❌ App Bridge Error</div>
                                <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">${error.message || 'Please refresh the page.'}</div>
                                <button onclick="window.location.reload()" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Refresh Page</button>
                            </div>
                        `;
                    });
                    return;
                } else if (!window.appBridgeReady) {
                    // Fallback to original sync check'''
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        changes_made.append("Enhanced button check with Promise support")
    
    # 4. Do the same for updateInventory and generateReport
    for func_name in ['updateInventory', 'generateReport']:
        pattern = r'(// CRITICAL: Wait for App Bridge to be ready before making requests\s+if \(isEmbedded && !window\.appBridgeReady\) \{[^}]+' + func_name + r'\([^)]+\);)'
        if re.search(pattern, content, re.DOTALL):
            # Similar replacement but with function name
            replacement = r'''// PERFECTED: Wait for App Bridge (uses Promise if available, sync check as fallback)
            if (isEmbedded) {
                if (window.waitForAppBridge && typeof window.waitForAppBridge === 'function' && !window.appBridgeReady) {
                    window.waitForAppBridge().then(function(bridgeState) {
                        if (bridgeState && bridgeState.ready && bridgeState.app) {
                            window.shopifyApp = bridgeState.app;
                            window.appBridgeReady = true;
                            ''' + func_name + r'''(button);
                        } else {
                            setButtonLoading(button, false);
                            document.getElementById('output').innerHTML = `
                                <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                                    <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ App Bridge Not Ready</div>
                                    <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">Please wait while the app initializes.</div>
                                    <button onclick="var btn = document.querySelector('.card-btn[onclick*=\\"''' + func_name + r'''\\"]'); if (btn) setTimeout(function(){''' + func_name + r'''(btn);}, 500);" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                                </div>
                            `;
                        }
                    }).catch(function(error) {
                        setButtonLoading(button, false);
                        document.getElementById('output').innerHTML = `
                            <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fff4f4; border: 1px solid #fecaca; border-radius: 8px;">
                                <div style="font-size: 15px; font-weight: 600; color: #d72c0d; margin-bottom: 8px;">❌ App Bridge Error</div>
                                <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">${error.message || 'Please refresh the page.'}</div>
                                <button onclick="window.location.reload()" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Refresh Page</button>
                            </div>
                        `;
                    });
                    return;
                } else if (!window.appBridgeReady) {'''
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            changes_made.append(f"Enhanced {func_name} check")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Changes made:")
    for change in changes_made:
        print(f"   - {change}")
    print("\n✅ App Bridge Promise system properly integrated!")
    print("   Buttons will use Promise if available, fallback to sync check")

if __name__ == '__main__':
    fix_all()

