/**
 * App Bridge Navigation and Handshake Hardening
 * Centrally managed script to prevent "Virtual 404" errors and maintain the Shopify context.
 */

(function () {
    // 1. Handshake Initialization
    const urlParams = new URLSearchParams(window.location.search);
    let host = urlParams.get('host') || window.HOST_PARAM;
    let shop = urlParams.get('shop') || window.SHOP_PARAM;

    // Persistence: If host is missing from URL, try sessionStorage (recovery mode)
    if (!host || host === 'None') {
        host = sessionStorage.getItem('shopify_host');
        if (host) {
            console.log('🔄 Restored host from sessionStorage:', host);
        }
    } else {
        sessionStorage.setItem('shopify_host', host);
    }

    if (!shop || shop === 'None') {
        shop = sessionStorage.getItem('shopify_shop');
    } else {
        sessionStorage.setItem('shopify_shop', shop);
    }

    const apiKey = window.SHOPIFY_API_KEY || '';

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

            window.shopify = app;
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

            // Expose Toast and TitleBar
            window.shopify.Toast = AppBridge.actions.Toast;
            window.shopify.TitleBar = AppBridge.actions.TitleBar;

            console.log('✅ App Bridge Handshake Successful');

            // 2. Global "Single-Entry" Interceptors
            // Re-define internalNav to use App Bridge Redirect
            window.internalNav = function (path) {
                console.log('🔀 App Bridge Redirect to:', path);
                redirectInstance.dispatch(Redirect.Action.APP, path);
            };

            // Global Navigation Helper as requested
            window.appNavigate = function (path) {
                // Ensure the path has shop and host if possible
                var dest = path;
                if (dest.indexOf('?') === -1 && window.location.search) {
                    dest += window.location.search;
                }
                window.internalNav(dest);
            };

            // Backwards compatibility
            window.openPage = window.appNavigate;

        } catch (e) {
            console.error('❌ App Bridge Handshake Failed:', e);
        }
    } else if (!host) {
        console.error('🚨 Missing host parameter - Handshake will fail');
    }

    // 3. Fallback Navigation (for when App Bridge isn't ready or initialized)
    if (!window.internalNav) {
        window.internalNav = function (path) {
            var dest = path;
            var sep = dest.indexOf('?') > -1 ? '&' : '?';
            if (shop && dest.indexOf('shop=') === -1) dest += sep + 'shop=' + encodeURIComponent(shop);
            if (host && dest.indexOf('host=') === -1) dest += (dest.indexOf('?') > -1 ? '&' : '?') + 'host=' + encodeURIComponent(host);
            window.location.href = dest;
        };
    }

    // 4. Click Interceptor
    document.addEventListener('click', function (e) {
        const link = e.target.closest('a');
        if (!link || !link.href) return;

        // Skip external, blank, or hash links
        if (link.target === '_blank' || !link.href.startsWith(window.location.origin)) return;
        const path = link.getAttribute('href');
        if (path === '#' || path.startsWith('javascript:')) return;

        e.preventDefault();
        window.internalNav(path);
    });

    // 5. Form Interceptor
    document.addEventListener('submit', function (e) {
        const form = e.target;
        if (form.method.toLowerCase() === 'get' && form.action.startsWith(window.location.origin)) {
            e.preventDefault();
            const formData = new FormData(form);
            const searchParams = new URLSearchParams(formData);
            const action = form.getAttribute('action');
            const path = action.split('?')[0].replace(window.location.origin, '') + '?' + searchParams.toString();
            window.internalNav(path);
        }
    });

})();
