/* Optional Dashboard JavaScript - Move inline scripts from dashboard.html here if needed */
/* This file is currently optional as dashboard.html uses inline scripts */

// Example JavaScript structure if externalizing scripts from dashboard template

// Global variables
window.appBridgeReady = false;
window.isEmbedded = false;

// Initialize App Bridge for Shopify embedded apps
function initializeAppBridge() {
    var urlParams = new URLSearchParams(window.location.search);
    var host = urlParams.get('host');
    var shop = urlParams.get('shop');

    window.isEmbedded = !!host;

    if (!host) {
        window.shopifyApp = null;
        window.appBridgeReady = true;
        return;
    }

    // App Bridge v4: exposes window.shopify automatically
    function init() {
        if (window.shopify) {
            window.shopifyApp = window.shopify;
            window.appBridgeReady = true;
            return;
        }
        setTimeout(init, 50);
    }
    init();
}

// Error logging functionality
function initializeErrorLogging() {
    // Store original console.error
    var originalConsoleError = console.error;
    var isLoggingError = false;

    // Function to log JavaScript errors to backend
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
                viewport: {
                    width: window.innerWidth,
                    height: window.innerHeight
                },
                session_id: 'js-session-' + Date.now()
            };

            fetch('/api/log_error', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(errorLog),
                credentials: 'include'
            }).catch(function(err) {
                originalConsoleError.call(console, 'Failed to log error to backend:', err);
            });
        } catch (e) {
            originalConsoleError.call(console, 'Error logging system failed:', e);
        } finally {
            isLoggingError = false;
        }
    }

    // Global error handler
    window.addEventListener('error', function(event) {
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
    window.addEventListener('unhandledrejection', function(event) {
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

// Navigation helper
window.openPage = function(path) {
    var params = new URLSearchParams(window.location.search);
    var shop = params.get('shop');
    var host = params.get('host');
    var embedded = params.get('embedded') || (host ? '1' : '');

    var sep = path.indexOf('?') > -1 ? '&' : '?';
    var dest = path;

    if (shop) dest += sep + 'shop=' + shop;
    if (host) dest += (dest.indexOf('?') > -1 ? '&' : '?') + 'host=' + host;
    if (embedded) dest += (dest.indexOf('?') > -1 ? '&' : '?') + 'embedded=' + embedded;

    window.location.href = dest;
    return false;
};

// API functions
window.processOrders = function(button) {
    // API call implementation would go here
    console.log('Process orders called');
};

window.updateInventory = function(button) {
    // API call implementation would go here
    console.log('Update inventory called');
};

window.generateReport = function(button) {
    // API call implementation would go here
    console.log('Generate report called');
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeAppBridge();
    initializeErrorLogging();

    // Add embedded class to body if needed
    if (window.isEmbedded && document.body) {
        document.body.classList.add('embedded');
    }

    console.log('Dashboard JavaScript initialized');
});

// Handle resource loading errors gracefully
window.addEventListener('error', function(e) {
    // Skip logging for missing static resources to reduce noise
    if (e.target && (e.target.tagName === 'LINK' || e.target.tagName === 'SCRIPT')) {
        console.warn('Resource failed to load:', e.target.src || e.target.href);
        return; // Don't log to backend
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
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
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
