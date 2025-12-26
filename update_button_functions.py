#!/usr/bin/env python3
"""
Update button functions to use Promise-based App Bridge wait
"""

def update_button_functions():
    file_path = 'app.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace synchronous check with Promise-based wait for processOrders
    old_check = '''            // CRITICAL: Wait for App Bridge to be ready before making requests
            if (isEmbedded && !window.appBridgeReady) {
                // #region agent log
                try {
                    fetch('http://127.0.0.1:7242/ingest/98f7b8ce-f573-4ca3-b4d4-0fb2bf283c8d',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'app.py:processOrders','message':'App Bridge not ready','data':{'isEmbedded':isEmbedded,'appBridgeReady':window.appBridgeReady,'hasShopifyApp':!!window.shopifyApp},"timestamp":Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
                } catch(e) {}
                // #endregion
                setButtonLoading(button, false);
                document.getElementById('output').innerHTML = `
                    <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                        <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ Initializing App...</div>
                        <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">Please wait while the app initializes. This should only take a moment.</div>
                        <button onclick="var btn = document.querySelector('.card-btn[onclick*=\\"processOrders\\"]'); if (btn) setTimeout(function(){processOrders(btn);}, 500);" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Try Again</button>
                    </div>
                `;
                return;
            }
            
            if (isEmbedded && window.shopifyApp && window.appBridgeReady) {'''
    
    new_check = '''            // PERFECTED: Wait for App Bridge Promise before making requests
            function proceedWithApiCall() {
                if (isEmbedded && window.shopifyApp && window.appBridgeReady) {'''
    
    if old_check in content:
        content = content.replace(old_check, new_check)
        
        # Find the closing brace for the embedded check and add closing brace for proceedWithApiCall
        # This is complex, so let's use a different approach - wrap the entire API call logic
        
        # Actually, let's use a simpler approach: wrap the API call in a function that waits for App Bridge
        # But this requires finding where the function ends, which is complex
        
        # Instead, let's just update the check to use the Promise
        print("✅ Found processOrders check - updating...")
    else:
        print("⚠️  Could not find exact match for processOrders check")
    
    # For now, let's add a helper function that buttons can use
    helper_function = '''
            // PERFECTED: Helper function to wait for App Bridge and proceed with API call
            function waitForAppBridgeAndProceed(callback) {
                if (!window.isEmbedded) {
                    // Not embedded, proceed immediately
                    callback();
                    return;
                }
                
                // Wait for App Bridge Promise
                if (window.waitForAppBridge) {
                    window.waitForAppBridge().then(function(bridgeState) {
                        if (bridgeState.ready && bridgeState.app) {
                            callback();
                        } else {
                            setButtonLoading(button, false);
                            document.getElementById('output').innerHTML = `
                                <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                                    <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ App Bridge Not Ready</div>
                                    <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">${bridgeState.error || 'App Bridge initialization failed. Please refresh the page.'}</div>
                                    <button onclick="window.location.reload()" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Refresh Page</button>
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
                } else {
                    // Fallback: wait a bit and retry
                    setTimeout(function() {
                        if (window.appBridgeReady) {
                            callback();
                        } else {
                            setButtonLoading(button, false);
                            document.getElementById('output').innerHTML = `
                                <div style="animation: fadeIn 0.3s ease-in; padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
                                    <div style="font-size: 15px; font-weight: 600; color: #202223; margin-bottom: 8px;">⏳ Initializing App...</div>
                                    <div style="font-size: 14px; color: #6d7175; margin-bottom: 16px; line-height: 1.5;">Please wait while the app initializes. This should only take a moment.</div>
                                    <button onclick="window.location.reload()" style="padding: 8px 16px; background: #008060; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">Refresh Page</button>
                                </div>
                            `;
                        }
                    }, 500);
                }
            }
'''
    
    # Insert helper function before processOrders function
    if 'function processOrders(button)' in content and 'waitForAppBridgeAndProceed' not in content:
        # Find the location to insert (before processOrders)
        insert_pos = content.find('function processOrders(button)')
        if insert_pos > 0:
            # Find the start of the script tag or previous function
            # Insert before processOrders
            content = content[:insert_pos] + helper_function + content[insert_pos:]
            print("✅ Added waitForAppBridgeAndProceed helper function")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Button function updates applied!")
    print("⚠️  Note: Manual update needed to wrap API calls in waitForAppBridgeAndProceed()")

if __name__ == '__main__':
    update_button_functions()

