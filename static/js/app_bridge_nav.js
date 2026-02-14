/**
 * App Bridge Navigation and Handshake Hardening (2026 Compliance)
 * Centrally managed script to prevent "Virtual 404" errors and maintain the Shopify context.
 */

(function () {
    'use strict';

    // 1. Handshake Initialization
    const urlParams = new URLSearchParams(window.location.search);
    let host = urlParams.get('host') || window.HOST_PARAM;
    let shop = urlParams.get('shop') || window.SHOP_PARAM;

    // Persistence: If host is missing from URL, try sessionStorage (recovery mode)
    if (!host || host === 'None') {
        host = sessionStorage.getItem('shopify_host');
    } else {
        sessionStorage.setItem('shopify_host', host);
    }

    if (!shop || shop === 'None') {
        shop = sessionStorage.getItem('shopify_shop');
    } else {
        sessionStorage.setItem('shopify_shop', shop);
    }

    const apiKey = window.SHOPIFY_API_KEY || '';

    // Initialization Flag
    window.appBridgeReady = false;

    if (host && window['app-bridge']) {
        try {
            const AppBridge = window['app-bridge'];
            const createApp = AppBridge.default;
            const Redirect = AppBridge.actions.Redirect;

            const app = createApp({
                apiKey: apiKey,
                host: host,
                forceRedirect: true
            });

            window.shopifyApp = app;
            window.shopify = app; // Alias for v4 compliance
            window.shopify.Redirect = Redirect;
            window.shopify.host = host;
            window.shopify.shop = shop;

            // Initialize global redirect instance
            const redirectInstance = Redirect.create(app);
            window.shopify.redirect = redirectInstance;

            // Expose idToken helper
            window.shopify.idToken = async () => {
                const getSessionToken = AppBridge.utilities.getSessionToken;
                return await getSessionToken(app);
            };

            // Modern v4 navigation alias
            window.shopify.navigate = function (path) {
                let relativePath = path;
                if (relativePath.startsWith(window.location.origin)) {
                    relativePath = relativePath.replace(window.location.origin, '');
                }
                console.log('[App Bridge 4.0] Navigating (via Redirect action):', relativePath);
                redirectInstance.dispatch(Redirect.Action.APP, relativePath);
            };

            // Expose Toast and TitleBar
            window.shopify.Toast = AppBridge.actions.Toast;
            window.shopify.TitleBar = AppBridge.actions.TitleBar;

            console.log('✅ App Bridge Handshake Successful');
            window.appBridgeReady = true;

            // 2. Global "Single-Entry" Interceptors
            window.internalNav = function (path) {
                window.shopify.navigate(path);
            };

            // Global Navigation Helper as requested by the user
            window.appNavigate = function (path) {
                window.internalNav(path);
            };

            // Backwards compatibility
            window.openPage = window.appNavigate;

        } catch (e) {
            console.error('❌ App Bridge Handshake Failed:', e);
        }
    }

    // 3. Fallback Navigation (for when App Bridge isn't ready)
    if (!window.internalNav) {
        window.internalNav = function (path) {
            console.warn('⚠️ App Bridge not ready, falling back to window.location. This may cause 404 loops in some contexts.');
            var dest = path;
            var sep = dest.indexOf('?') > -1 ? '&' : '?';
            if (shop && dest.indexOf('shop=') === -1) dest += sep + 'shop=' + encodeURIComponent(shop);
            if (host && dest.indexOf('host=') === -1) dest += (dest.indexOf('?') > -1 ? '&' : '?') + 'host=' + encodeURIComponent(host);
            window.location.href = dest;
        };
        window.appNavigate = window.internalNav;
        window.openPage = window.internalNav;
    }

    // 4. Global Interceptors (Click & Form)
    function initializeInterceptors() {
        // Link Interceptor
        document.addEventListener('click', function (e) {
            const link = e.target.closest('a');
            if (!link || !link.href) return;

            // Skip external, blank, or hash links
            if (link.target === '_blank' || !link.href.startsWith(window.location.origin)) return;

            // Skip static files (important for downloads/media)
            if (link.href.includes('/static/')) return;

            const path = link.getAttribute('href');
            if (path === '#' || path.startsWith('javascript:')) return;

            console.log('🔗 Intercepted click on:', path);
            e.preventDefault();
            window.internalNav(path);
        }, true); // Use capture phase to intercept early

        // Form Interceptor
        document.addEventListener('submit', function (e) {
            const form = e.target;
            // Only intercept GET forms (navigation forms)
            if (form.method.toLowerCase() === 'get' && form.action.startsWith(window.location.origin)) {
                e.preventDefault();
                const formData = new FormData(form);
                const searchParams = new URLSearchParams(formData);
                const action = form.getAttribute('action');
                const path = action.split('?')[0].replace(window.location.origin, '') + '?' + searchParams.toString();

                console.log('📋 Intercepted form submission to:', path);
                window.internalNav(path);
            }
        }, true);
    }

    // 5. Visibility Guardian: Ensure app becomes visible
    const setAppReady = () => {
        const body = document.body;
        if (!body) {
            // [SAFETY] If body isn't ready, wait 50ms and try again
            console.log('⏳ Waiting for body...');
            setTimeout(setAppReady, 50);
            return;
        }
        body.classList.add('app-ready');
        window.appBridgeReady = true;
        console.log('✨ App Visibility: Ready');
    };

    function init() {
        // Initialize interceptors
        initializeInterceptors();

        // If handshake was successful, set ready
        if (window.appBridgeReady) {
            setAppReady();
        } else {
            // Safety Timeout: 3 seconds to show something even if handshake is slow/failing
            setTimeout(() => {
                if (document.body && !document.body.classList.contains('app-ready')) {
                    console.warn('⚠️ Handshake timeout - forcing visibility');
                    setAppReady();
                }
            }, 3000);

            // Also listen for successful handshake if it happens later
            const checkReady = setInterval(() => {
                if (window.appBridgeReady) {
                    clearInterval(checkReady);
                    setAppReady();
                }
            }, 100);
        }

        console.log('🚀 App Bridge Navigation Guardian Active');
    }

    // MAIN EXECUTION GUARD
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
