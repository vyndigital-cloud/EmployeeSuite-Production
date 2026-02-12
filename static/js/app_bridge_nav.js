// App Bridge Authenticated Navigation Helper
// UPDATED for 2026 Shopify Compliance - Uses App Bridge 4.0

(function () {
    'use strict';

    // Wait for App Bridge to be ready
    function waitForAppBridge(callback) {
        if (window.shopify && window.shopify.idToken) {
            callback();
        } else {
            setTimeout(() => waitForAppBridge(callback), 100);
        }
    }

    // 2026 COMPLIANT: "Tokenize" navigation - append token to URL
    async function navigateAuthenticated(url) {
        try {
            // Get fresh session token
            const token = await window.shopify.idToken();

            // CRITICAL: Append token to URL (page loads can't use headers!)
            const urlObj = new URL(url, window.location.origin);
            urlObj.searchParams.set('id_token', token);

            const finalPath = urlObj.pathname + urlObj.search;

            // Use App Bridge navigate (preferred - 2026 compliant)
            if (window.shopify && window.shopify.navigate) {
                window.shopify.navigate(finalPath);
                console.log('[Auth Nav 2026] App Bridge navigation with token:', finalPath);
            } else {
                // Fallback to direct navigation
                window.location.href = urlObj.toString();
                console.log('[Auth Nav 2026] Legacy fallback:', urlObj.toString());
            }
        } catch (error) {
            console.error('[Auth Nav 2026] Token fetch failed:', error);
            // Last resort fallback (no token)
            window.location.href = url;
        }
    }

    // Convert all internal links to use authenticated navigation
    function enhanceLinks() {
        // Find all internal links
        const links = document.querySelectorAll('a[href]');

        links.forEach(link => {
            const href = link.getAttribute('href');

            // Skip external links, anchors, and special protocols
            if (!href || href.startsWith('#') || href.startsWith('http') ||
                href.startsWith('mailto:') || href.startsWith('tel:')) {
                return;
            }

            // Skip already enhanced links
            if (link.dataset.authEnhanced) {
                return;
            }

            // Skip static files
            if (href.includes('/static/')) {
                return;
            }

            // Mark as enhanced
            link.dataset.authEnhanced = 'true';

            // Intercept clicks
            link.addEventListener('click', function (e) {
                // Let Cmd/Ctrl+Click open in new tab normally
                if (e.metaKey || e.ctrlKey) {
                    return;
                }

                e.preventDefault();
                const targetUrl = this.href;

                console.log('[Auth Nav 2026] Navigating with App Bridge:', targetUrl);
                navigateAuthenticated(targetUrl);
            });
        });
    }

    // SAFETY NET: Global click interceptor (catches sidebar, settings, subscribe, etc.)
    document.addEventListener('click', async (event) => {
        const link = event.target.closest('a');

        // Skip if not a link
        if (!link) return;

        // Skip if already processed by individual handler
        if (link.dataset.authEnhanced) return;

        // Only intercept internal links
        const href = link.href || link.getAttribute('href');
        if (!href ||
            !href.includes(window.location.origin) ||
            href.startsWith('#') ||
            href.startsWith('mailto:') ||
            href.startsWith('tel:') ||
            href.includes('/static/')) {
            return;
        }

        // Let Cmd/Ctrl+Click open in new tab
        if (event.metaKey || event.ctrlKey) return;

        event.preventDefault();

        console.log('[Auth Nav 2026] Safety Net: Intercepted unprocessed link:', href);

        try {
            const token = await window.shopify.idToken();
            const url = new URL(href);
            url.searchParams.set('id_token', token);

            // Preserve shop/host from current URL
            const params = new URLSearchParams(window.location.search);
            ['shop', 'host'].forEach(param => {
                if (params.has(param)) {
                    url.searchParams.set(param, params.get(param));
                }
            });

            const finalPath = url.pathname + url.search;

            if (window.shopify && window.shopify.navigate) {
                window.shopify.navigate(finalPath);
            } else {
                window.location.href = url.toString();
            }
        } catch (error) {
            console.error('[Auth Nav 2026] Safety Net failed:', error);
            window.location.href = href; // Fallback
        }
    });

    // Initialize when App Bridge is ready
    waitForAppBridge(function () {
        console.log('[Auth Nav 2026] App Bridge ready - 2026 compliant mode ✅');

        // Enhance existing links
        enhanceLinks();

        // Watch for dynamically added links
        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.addedNodes.length) {
                    enhanceLinks();
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        console.log('[Auth Nav 2026] ✅ Global event delegation + individual link enhancement active');
    });

    // Expose for manual use
    window.navigateAuthenticated = navigateAuthenticated;
})();
