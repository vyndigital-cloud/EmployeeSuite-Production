/* Dashboard JavaScript - All functionality moved here from template */

// Global variables
window.appBridgeReady = false;
window.isEmbedded = false;
window.shopifyApp = null;

// Request management
var activeRequests = {
    processOrders: null,
    updateInventory: null,
    generateReport: null
};

var debounceTimers = {
    processOrders: null,
    updateInventory: null,
    generateReport: null
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    initializeApp();
});

function initializeApp() {
    // Initialize App Bridge
    initializeAppBridge();

    // Initialize error logging
    initializeErrorLogging();

    // Set up event listeners
    setupEventListeners();

    // Initialize network status
    updateConnectionStatus();

    // Check store connection status via JWT
    checkStoreStatus();

    console.log('Dashboard JavaScript fully initialized');
}

// Initialize App Bridge for Shopify embedded apps
function initializeAppBridge() {
    // App Bridge v4: Get shop and host from URL or App Bridge config
    var urlParams = new URLSearchParams(window.location.search);
    var host = urlParams.get('host');
    var shop = urlParams.get('shop');

    // Robust Fallback: Use window.shopify.config if parameters are missing
    if (!shop && window.shopify && window.shopify.config) {
        shop = window.shopify.config.shop;
        console.log('🔗 Falling back to window.shopify.config.shop:', shop);
    }

    if (!host && window.shopify && window.shopify.config) {
        host = window.shopify.config.host;
        console.log('🔗 Falling back to window.shopify.config.host:', host);
    }

    window.isEmbedded = !!host;
    window.SHOP_PARAM = shop || '';
    window.HOST_PARAM = host || '';

    if (!host) {
        window.shopifyApp = null;
        window.appBridgeReady = true;
        return;
    }

    // App Bridge v4: Wait for shopify object and get session token
    var initAttempts = 0;
    var maxAttempts = 50;

    async function init() {
        initAttempts++;
        if (window.shopify && window.shopify.idToken) {
            window.shopifyApp = window.shopify;

            // FIX 1: Properly await the token (it returns a Promise)
            try {
                const token = await window.shopify.idToken();
                console.log('✅ Session token retrieved successfully');

                // Store for backward compatibility (but prefer fresh fetch)
                window.sessionToken = token;

            } catch (e) {
                console.error('❌ Failed to get session token:', e);
            }

            // FIX 2: Only set ready AFTER token is secured
            window.appBridgeReady = true;
            return;
        }
        if (initAttempts >= maxAttempts) {
            console.warn('⚠️ App Bridge timeout - falling back');
            window.appBridgeReady = true;
            return;
        }
        setTimeout(init, 100);
    }
    init();
}

// Replace standard fetch with this Authenticated Fetch
async function authenticatedFetch(url, options = {}) {
    // Fallback to standard fetch if not embedded
    if (!window.isEmbedded || !window.shopify) {
        return fetch(url, options);
    }

    try {
        // Get fresh JWT from Shopify - this is a promise
        const sessionToken = await window.shopify.idToken();

        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${sessionToken}`,
            'X-Requested-With': 'XMLHttpRequest'
        };

        // CRITICAL: Omit cookies to prevent Safari from blocking the request in iframes
        options.credentials = 'omit';

        return fetch(url, options);
    } catch (e) {
        console.error('JWT Fetch Error:', e);
        return fetch(url, options);
    }
}

// Check store connection status via JWT
function checkStoreStatus() {
    if (!window.isEmbedded) return;

    authenticatedFetch('/api/store/status')
        .then(res => res.json())
        .then(data => {
            if (data.is_connected) {
                console.log('Store is connected (verified via JWT)');
                const connectSec = document.getElementById('connect-section');
                const mainDash = document.getElementById('main-dash');

                if (connectSec) connectSec.style.display = 'none';
                if (mainDash) mainDash.style.display = 'block';
            } else {
                console.log('Store is not connected according to API');
                const connectSec = document.getElementById('connect-section');
                const mainDash = document.getElementById('main-dash');

                if (connectSec) connectSec.style.display = 'block';
                if (mainDash) mainDash.style.display = 'none';
            }
        })
        .catch(err => {
            console.error('Error checking store status:', err);
        });
}

// DEPRECATED: Sentinel.js now handles all token injection globally
// This function is no longer needed but kept for reference
function setupSessionTokenFetch() {
    console.log('ℹ️ Token injection handled by Sentinel.js (global fetch interceptor)');
    // No-op: Sentinel already intercepts ALL fetch requests
}

// Error logging functionality
function initializeErrorLogging() {
    var originalConsoleError = console.error;
    var isLoggingError = false;

    function logJavaScriptError(errorType, errorMessage, errorLocation, errorData, stackTrace) {
        if (isLoggingError) {
            originalConsoleError.call(console, '[ERROR LOGGED]', errorType, ':', errorMessage);
            return;
        }

        isLoggingError = true;
        try {
            var errorLog = {
                timestamp: new Date().toISOString(),
                error_type: errorType,
                error_message: errorMessage,
                error_location: errorLocation,
                stack_trace: stackTrace,
                error_data: errorData || {},
                user_agent: navigator.userAgent,
                url: window.location.href,
                referer: document.referrer,
                session_id: 'js-session-' + Date.now()
            };

            authenticatedFetch('/api/log_error', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(errorLog)
            }).catch(function (err) {
                originalConsoleError.call(console, 'Failed to log error to backend:', err);
            });
        } catch (e) {
            originalConsoleError.call(console, 'Error logging system failed:', e);
        } finally {
            isLoggingError = false;
        }
    }

    // Global error handler
    window.addEventListener('error', function (event) {
        logJavaScriptError(
            'JavaScriptError',
            event.message || 'Unknown error',
            event.filename + ':' + event.lineno + ':' + event.colno,
            {
                error: event.error ? event.error.toString() : null,
                type: event.type,
                target: event.target ? event.target.tagName : null
            },
            event.error ? (event.error.stack || 'No stack trace') : 'No stack trace'
        );
    }, true);

    // Unhandled promise rejection handler
    window.addEventListener('unhandledrejection', function (event) {
        var error = event.reason;
        var errorMessage = error ? (error.message || error.toString() || 'Unhandled promise rejection') : 'Unknown promise rejection';
        var stackTrace = error && error.stack ? error.stack : 'No stack trace';

        logJavaScriptError(
            'UnhandledPromiseRejection',
            errorMessage,
            'Promise rejection',
            {
                reason: error ? error.toString() : null,
                promise: event.promise ? event.promise.toString() : null
            },
            stackTrace
        );

        event.preventDefault();
    });
}

// Set up all event listeners
function setupEventListeners() {
    // Button click handling with event delegation
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.card-btn[data-action]');
        if (!btn) return;

        var action = btn.getAttribute('data-action');
        if (!action || btn.disabled) return;

        e.preventDefault();
        e.stopPropagation();

        // Route to appropriate function
        if (window[action] && typeof window[action] === 'function') {
            try {
                window[action](btn);
            } catch (err) {
                console.error('Error executing function:', action, err);
                showErrorMessage('An error occurred. Please refresh the page and try again.');
            }
        } else {
            console.error('Function not found for action:', action);
        }
    });

    // Network status listeners
    window.addEventListener('online', function () {
        updateConnectionStatus();
    });

    window.addEventListener('offline', function () {
        updateConnectionStatus();
    });
}

// Network status detection
function updateConnectionStatus() {
    var isOnline = navigator.onLine;
    var statusEl = document.getElementById('connection-status');
    if (statusEl) {
        if (isOnline) {
            statusEl.style.display = 'none';
        } else {
            statusEl.style.display = 'block';
            statusEl.innerHTML = '<div style="padding: 8px 16px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 6px; font-size: 13px; color: #202223; text-align: center;">⚠️ No internet connection</div>';
        }
    }
}

// Utility functions
function showErrorMessage(message) {
    var outputEl = document.getElementById('output');
    if (outputEl) {
        outputEl.innerHTML = '<div style="padding: 20px; background: #fff4f4; border: 1px solid #fecaca; border-radius: 8px;"><div style="color: #d72c0d; font-weight: 600;">' + message + '</div></div>';
    }
}

function setButtonLoading(button, isLoading) {
    if (isLoading) {
        button.disabled = true;
        button.style.opacity = '0.7';
        button.style.cursor = 'wait';
        var originalText = button.innerHTML;
        button.dataset.originalText = originalText;
        button.innerHTML = '<span style="display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.6s linear infinite; margin-right: 8px;"></span>Loading...';
    } else {
        button.disabled = false;
        button.style.opacity = '1';
        button.style.cursor = 'pointer';
        if (button.dataset.originalText) {
            button.innerHTML = button.dataset.originalText;
            delete button.dataset.originalText;
        }
    }
}

function showLoading(message) {
    document.getElementById('output').innerHTML = '<div class="loading"><div class="spinner"></div><div class="loading-text">' + message + '</div></div>';
}

// Global function to show subscribe prompt
window.showSubscribePrompt = function () {
    var outputEl = document.getElementById('output');
    if (!outputEl) return;

    // Get shop/host params for URL
    var params = new URLSearchParams(window.location.search);
    var shop = params.get('shop') || window.SHOP_PARAM || '';
    var host = params.get('host') || window.HOST_PARAM || '';

    var subscribeUrl = '/subscribe';
    var sep = '?';
    if (shop) { subscribeUrl += sep + 'shop=' + encodeURIComponent(shop); sep = '&'; }
    if (host) { subscribeUrl += sep + 'host=' + encodeURIComponent(host); }

    outputEl.innerHTML = `
        <div style="padding: 40px; background: #fff; border-radius: 16px; border: 1px solid #e5e7eb; text-align: center; animation: fadeIn 0.3s ease-in; max-width: 500px; margin: 0 auto; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
            <div style="margin-bottom: 20px; display: inline-flex; align-items: center; justify-content: center; width: 64px; height: 64px; background: #FEF2F2; border-radius: 50%;">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
            </div>
            <h3 style="color: #111827; margin-bottom: 8px; font-size: 20px; font-weight: 700;">Subscription Required</h3>
            <p style="color: #6B7280; margin-bottom: 24px; font-size: 15px; line-height: 1.5;">This feature is available with Employee Suite Pro. Subscribe to unlock full access.</p>
            <a href="${subscribeUrl}" onclick="openPage('${subscribeUrl}'); return false;" style="display: inline-block; background: #2563EB; color: #fff; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 15px; transition: all 0.2s; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">Upgrade Now →</a>
            <p style="color: #9CA3AF; margin-top: 16px; font-size: 13px;">$39/month • 7-day money-back guarantee</p>
        </div>
    `;
};

function cancelPreviousRequest(requestType) {
    if (activeRequests[requestType] && activeRequests[requestType].abort) {
        activeRequests[requestType].abort();
        activeRequests[requestType] = null;
    }
}

// API functions - 2026 COMPLIANT (async/await + authenticatedFetch)
window.processOrders = async function (button) {
    if (debounceTimers.processOrders) return;

    if (!navigator.onLine) {
        showErrorMessage('No internet connection. Please check your network and try again.');
        return;
    }

    cancelPreviousRequest('processOrders');
    setButtonLoading(button, true);
    showLoading('Loading orders...');

    try {
        // FIX: Use authenticatedFetch (handles token + credentials automatically)
        const response = await authenticatedFetch('/api/process_orders');

        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            document.getElementById('output').innerHTML = '<div style="animation: fadeIn 0.3s ease-in;"><h3 class="success">✅ Orders Loaded</h3><div style="margin-top: 12px;">' + (data.html || data.message || 'Orders processed successfully') + '</div></div>';
        } else if (data.action === 'subscribe') {
            window.showSubscribePrompt();
        } else {
            document.getElementById('output').innerHTML = '<div style="color: #dc2626;">' + (data.error || 'Failed to load orders') + '</div>';
        }
    } catch (err) {
        console.error('processOrders error:', err);
        showErrorMessage('Unable to connect to server. Please try again.');
    } finally {
        setButtonLoading(button, false);
        activeRequests.processOrders = null;
    }
};

window.updateInventory = async function (button) {
    if (debounceTimers.updateInventory) return;

    if (!navigator.onLine) {
        showErrorMessage('No internet connection. Please check your network and try again.');
        return;
    }

    cancelPreviousRequest('updateInventory');
    setButtonLoading(button, true);
    showLoading('Loading inventory...');

    try {
        // FIX: Use authenticatedFetch (handles token + credentials automatically)
        const response = await authenticatedFetch('/api/update_inventory');

        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            document.getElementById('output').innerHTML = '<div style="animation: fadeIn 0.3s ease-in;"><h3 class="success">✅ Inventory Updated</h3><div style="margin-top: 12px;">' + (data.html || data.message || 'Inventory updated successfully') + '</div></div>';
        } else if (data.action === 'subscribe') {
            window.showSubscribePrompt();
        } else {
            document.getElementById('output').innerHTML = '<div style="color: #dc2626;">' + (data.error || 'Failed to update inventory') + '</div>';
        }
    } catch (err) {
        console.error('updateInventory error:', err);
        showErrorMessage('Unable to connect to server. Please try again.');
    } finally {
        setButtonLoading(button, false);
        activeRequests.updateInventory = null;
    }
};

window.generateReport = async function (button) {
    if (debounceTimers.generateReport) return;

    if (!navigator.onLine) {
        showErrorMessage('No internet connection. Please check your network and try again.');
        return;
    }

    cancelPreviousRequest('generateReport');
    setButtonLoading(button, true);
    showLoading('Generating report...');

    try {
        // FIX: Use authenticatedFetch (handles token + credentials automatically)
        const response = await authenticatedFetch('/api/generate_report');

        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            document.getElementById('output').innerHTML = '<div style="animation: fadeIn 0.3s ease-in;"><h3 class="success">✅ Revenue Report Generated</h3><div style="margin-top: 12px;">' + (data.html || data.message || 'Report generated successfully') + '</div></div>';
        } else if (data.action === 'subscribe') {
            window.showSubscribePrompt();
        } else {
            document.getElementById('output').innerHTML = '<div style="color: #dc2626;">' + (data.error || 'Failed to generate report') + '</div>';
        }
    } catch (err) {
        console.error('generateReport error:', err);
        showErrorMessage('Unable to connect to server. Please try again.');
    } finally {
        setButtonLoading(button, false);
        activeRequests.generateReport = null;
    }
};


// Handle resource loading errors gracefully
window.addEventListener('error', function (e) {
    if (e.target && (e.target.tagName === 'LINK' || e.target.tagName === 'SCRIPT')) {
        console.warn('Resource failed to load:', e.target.src || e.target.href);
        return;
    }
}, true);

// Ensure all HTML content is properly escaped when building dynamic content
function escapeHtml(text) {
    var map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function (m) { return map[m]; });
}

// Safe HTML builder for dynamic content
function buildHtmlContent(data) {
    var html = '';
    if (data && typeof data === 'object') {
        for (var key in data) {
            if (data.hasOwnProperty(key)) {
                html += '<div class="data-item">';
                html += '<span class="key">' + escapeHtml(String(key)) + ':</span> ';
                html += '<span class="value">' + escapeHtml(String(data[key])) + '</span>';
                html += '</div>';
            }
        }
    }
    return html;
}
