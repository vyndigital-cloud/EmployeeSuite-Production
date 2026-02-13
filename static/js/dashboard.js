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

    console.log('Dashboard JavaScript fully initialized');
}

// Initialize App Bridge for Shopify embedded apps
function initializeAppBridge() {
    var urlParams = new URLSearchParams(window.location.search);
    var host = urlParams.get('host');
    var shop = urlParams.get('shop');

    window.isEmbedded = !!host;
    // CRITICAL: Preserve template-injected values for dev mode
    window.SHOP_PARAM = shop || window.SHOP_PARAM || '';
    window.HOST_PARAM = host || window.HOST_PARAM || '';
    window.ID_TOKEN = urlParams.get('id_token') || '';

    if (!host) {
        window.shopifyApp = null;
        window.appBridgeReady = true;
        return;
    }

    // App Bridge v4: Wait for shopify object and get session token
    var initAttempts = 0;
    var maxAttempts = 50;

    function init() {
        initAttempts++;
        if (window.shopify && window.shopify.idToken) {
            window.shopifyApp = window.shopify;

            // CRITICAL: Get session token for API authentication
            try {
                window.sessionToken = window.shopify.idToken();
                console.log('Session token retrieved successfully');

                // [REMOVED] Redundant fetch interceptor - now handled by layout_polaris.html
                // setupSessionTokenFetch();

            } catch (e) {
                console.error('Failed to get session token:', e);
            }

            window.appBridgeReady = true;
            return;
        }
        if (initAttempts >= maxAttempts) {
            console.warn('App Bridge initialization timeout - falling back to cookie auth');
            window.appBridgeReady = true;
            return;
        }
        setTimeout(init, 100);
    }
    init();
}

// [REMOVED] setupSessionTokenFetch logic - now handled by layout_polaris.html

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

            fetch('/api/log_error', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(errorLog),
                credentials: 'include'
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

// API functions - comprehensive implementations
window.processOrders = async function (button) {
    if (debounceTimers.processOrders) return;

    if (!navigator.onLine) {
        showErrorMessage('No internet connection. Please check your network and try again.');
        return;
    }

    cancelPreviousRequest('processOrders');
    setButtonLoading(button, true);
    showLoading('Loading orders...');

    var controller = new AbortController();
    activeRequests.processOrders = controller;

    var apiUrl = '/api/process_orders';
    if (window.SHOP_PARAM) {
        apiUrl += '?shop=' + encodeURIComponent(window.SHOP_PARAM);
    }

    var fetchOptions = {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        signal: controller.signal
    };

    // CRITICAL: Await session token for embedded apps
    // This resolves the [object Promise] bug
    if (window.shopify && typeof window.shopify.idToken === 'function') {
        try {
            window.sessionToken = await window.shopify.idToken();
        } catch (e) {
            console.error("Failed to retrieve Shopify ID Token", e);
        }
    }

    if (window.sessionToken) {
        fetchOptions.headers['Authorization'] = 'Bearer ' + window.sessionToken;
    }

    fetch(apiUrl, fetchOptions)
        .then(async r => {
            if (controller.signal.aborted) return null;

            // Handle session token expiry
            if (r.status === 401 && window.shopify && window.shopify.idToken) {
                // Refresh token and retry
                try {
                    console.log('Token expired, refreshing...');
                    window.sessionToken = await window.shopify.idToken();
                    // Retry the request with new token
                    fetchOptions.headers['Authorization'] = 'Bearer ' + window.sessionToken;
                    return fetch(apiUrl, fetchOptions);
                } catch (e) {
                    console.error('Token refresh failed:', e);
                }
            }

            if (!r.ok) throw new Error('Request failed');
            return r.json();
        })
        .then(d => {
            if (!d) return;

            setButtonLoading(button, false);
            activeRequests.processOrders = null;

            if (d.success) {
                document.getElementById('output').innerHTML = '<div style="animation: fadeIn 0.3s ease-in;"><h3 class="success">✅ Orders Loaded</h3><div style="margin-top: 12px;">' + (d.html || d.message || 'Orders processed successfully') + '</div></div>';
            } else if (d.action === 'subscribe') {
                window.showSubscribePrompt();
            } else {
                document.getElementById('output').innerHTML = '<div style="color: #dc2626;">' + (d.error || 'Failed to load orders') + '</div>';
            }
        })
        .catch(err => {
            if (err.name === 'AbortError') return;
            setButtonLoading(button, false);
            activeRequests.processOrders = null;
            showErrorMessage('Unable to connect to server. Please try again.');
        });
};

window.updateInventory = function (button) {
    if (debounceTimers.updateInventory) return;

    if (!navigator.onLine) {
        showErrorMessage('No internet connection. Please check your network and try again.');
        return;
    }

    cancelPreviousRequest('updateInventory');
    setButtonLoading(button, true);
    showLoading('Loading inventory...');

    var controller = new AbortController();
    activeRequests.updateInventory = controller;

    var apiUrl = '/api/update_inventory';
    if (window.SHOP_PARAM) {
        apiUrl += '?shop=' + encodeURIComponent(window.SHOP_PARAM);
    }

    var fetchOptions = {
        credentials: 'include',
        signal: controller.signal
    };

    // CRITICAL: Add session token for embedded apps
    if (window.sessionToken) {
        fetchOptions.headers = fetchOptions.headers || {};
        fetchOptions.headers['Authorization'] = 'Bearer ' + window.sessionToken;
    }

    fetch(apiUrl, fetchOptions)
        .then(r => {
            if (controller.signal.aborted) return null;

            // Handle session token expiry
            if (r.status === 401 && window.shopify && window.shopify.idToken) {
                // Refresh token and retry
                try {
                    window.sessionToken = window.shopify.idToken();
                    // Retry the request with new token
                    fetchOptions.headers['Authorization'] = 'Bearer ' + window.sessionToken;
                    return fetch(apiUrl, fetchOptions);
                } catch (e) {
                    console.error('Token refresh failed:', e);
                }
            }

            if (!r.ok) throw new Error('Request failed');
            return r.json();
        })
        .then(d => {
            if (!d) return;

            setButtonLoading(button, false);
            activeRequests.updateInventory = null;

            if (d.success) {
                document.getElementById('output').innerHTML = '<div style="animation: fadeIn 0.3s ease-in;"><h3 class="success">✅ Inventory Updated</h3><div style="margin-top: 12px;">' + (d.html || d.message || 'Inventory updated successfully') + '</div></div>';
            } else if (d.action === 'subscribe') {
                window.showSubscribePrompt();
            } else {
                document.getElementById('output').innerHTML = '<div style="color: #dc2626;">' + (d.error || 'Failed to update inventory') + '</div>';
            }
        })
        .catch(err => {
            if (err.name === 'AbortError') return;
            setButtonLoading(button, false);
            activeRequests.updateInventory = null;
            showErrorMessage('Unable to connect to server. Please try again.');
        });
};

window.generateReport = function (button) {
    if (debounceTimers.generateReport) return;

    if (!navigator.onLine) {
        showErrorMessage('No internet connection. Please check your network and try again.');
        return;
    }

    cancelPreviousRequest('generateReport');
    setButtonLoading(button, true);
    showLoading('Generating report...');

    var controller = new AbortController();
    activeRequests.generateReport = controller;

    var apiUrl = '/api/generate_report';
    if (window.SHOP_PARAM) {
        apiUrl += '?shop=' + encodeURIComponent(window.SHOP_PARAM);
    }

    var fetchOptions = {
        credentials: 'include',
        signal: controller.signal
    };

    // CRITICAL: Add session token for embedded apps
    if (window.sessionToken) {
        fetchOptions.headers = fetchOptions.headers || {};
        fetchOptions.headers['Authorization'] = 'Bearer ' + window.sessionToken;
    }

    fetch(apiUrl, fetchOptions)
        .then(r => {
            if (controller.signal.aborted) return null;

            // Handle session token expiry
            if (r.status === 401 && window.shopify && window.shopify.idToken) {
                // Refresh token and retry
                try {
                    window.sessionToken = window.shopify.idToken();
                    // Retry the request with new token
                    fetchOptions.headers['Authorization'] = 'Bearer ' + window.sessionToken;
                    return fetch(apiUrl, fetchOptions);
                } catch (e) {
                    console.error('Token refresh failed:', e);
                }
            }

            if (!r.ok) throw new Error('Request failed');
            return r.json();
        })
        .then(d => {
            if (!d) return;

            setButtonLoading(button, false);
            activeRequests.generateReport = null;

            if (d.success) {
                document.getElementById('output').innerHTML = '<div style="animation: fadeIn 0.3s ease-in;"><h3 class="success">✅ Revenue Report Generated</h3><div style="margin-top: 12px;">' + (d.html || d.message || 'Report generated successfully') + '</div></div>';
            } else if (d.action === 'subscribe') {
                window.showSubscribePrompt();
            } else {
                document.getElementById('output').innerHTML = '<div style="color: #dc2626;">' + (d.error || 'Failed to generate report') + '</div>';
            }
        })
        .catch(err => {
            if (err.name === 'AbortError') return;
            setButtonLoading(button, false);
            activeRequests.generateReport = null;
            showErrorMessage('Unable to connect to server. Please try again.');
        });
};

// Navigation helper - Single Entry Point
// REMOVED: Redundant override moved to app_bridge_nav.js
// window.internalNav = function (path) { ... };
// window.openPage = window.internalNav;

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
