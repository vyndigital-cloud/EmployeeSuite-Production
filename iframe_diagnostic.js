// Diagnostic script to run in the iframe's console (not parent)
// This checks why buttons are frozen

(function() {
    console.log('🔍 Starting button diagnostic...');
    
    // Check 1: Are functions defined?
    var funcCheck = {
        processOrders: typeof window.processOrders,
        updateInventory: typeof window.updateInventory,
        generateReport: typeof window.generateReport
    };
    console.log('Function check:', funcCheck);
    
    // Check 2: Do buttons exist?
    var buttons = {
        processOrders: document.querySelector('.card-btn[onclick*="processOrders"]'),
        updateInventory: document.querySelector('.card-btn[onclick*="updateInventory"]'),
        generateReport: document.querySelector('.card-btn[onclick*="generateReport"]')
    };
    console.log('Button elements:', buttons);
    
    // Check 3: Button state
    for (var key in buttons) {
        if (buttons[key]) {
            var btn = buttons[key];
            var state = {
                exists: true,
                disabled: btn.disabled,
                onclick: btn.getAttribute('onclick'),
                pointerEvents: window.getComputedStyle(btn).pointerEvents,
                display: window.getComputedStyle(btn).display,
                visibility: window.getComputedStyle(btn).visibility,
                zIndex: window.getComputedStyle(btn).zIndex,
                cursor: window.getComputedStyle(btn).cursor
            };
            console.log('Button state for ' + key + ':', state);
            
            // Check if something is covering it
            var rect = btn.getBoundingClientRect();
            var elementAtPoint = document.elementFromPoint(rect.left + rect.width/2, rect.top + rect.height/2);
            if (elementAtPoint !== btn && !btn.contains(elementAtPoint)) {
                console.warn('⚠️ Something is covering button ' + key + ':', elementAtPoint);
            }
        } else {
            console.warn('❌ Button not found: ' + key);
        }
    }
    
    // Check 4: JavaScript errors
    var errors = [];
    window.addEventListener('error', function(e) {
        errors.push({
            message: e.message,
            filename: e.filename,
            lineno: e.lineno,
            colno: e.colno
        });
        console.error('JS Error:', e.message, 'at', e.filename + ':' + e.lineno);
    }, true);
    
    // Check 5: Try to manually call function
    console.log('Testing manual function call...');
    if (typeof window.processOrders === 'function') {
        try {
            var testBtn = buttons.processOrders;
            if (testBtn) {
                console.log('Attempting to call processOrders with button...');
                window.processOrders(testBtn);
            }
        } catch(e) {
            console.error('Error calling processOrders:', e);
        }
    }
    
    // Check 6: App Bridge state
    console.log('App Bridge state:', {
        isEmbedded: window.isEmbedded,
        appBridgeReady: window.appBridgeReady,
        hasShopifyApp: !!window.shopifyApp,
        waitForAppBridge: typeof window.waitForAppBridge
    });
    
    // Check 7: Add click listeners as backup
    for (var key in buttons) {
        if (buttons[key]) {
            buttons[key].addEventListener('click', function(e, name) {
                return function(ev) {
                    console.log('✅ Click captured via event listener for:', name);
                    console.log('Event details:', {
                        type: ev.type,
                        target: ev.target.tagName,
                        defaultPrevented: ev.defaultPrevented,
                        bubbles: ev.bubbles
                    });
                };
            }(buttons[key], key), true);
            console.log('Added backup click listener to:', key);
        }
    }
    
    console.log('✅ Diagnostic complete. Now try clicking the buttons and watch for logs.');
    
    // Return diagnostic results
    return {
        functions: funcCheck,
        buttons: Object.keys(buttons).map(function(k) { return {name: k, exists: !!buttons[k]}; }),
        appBridge: {
            isEmbedded: window.isEmbedded,
            appBridgeReady: window.appBridgeReady,
            hasShopifyApp: !!window.shopifyApp
        }
    };
})();


<<<<<<< HEAD


=======
>>>>>>> 435f7f080afbe6538bc4e1b20a026900b2acdce6





