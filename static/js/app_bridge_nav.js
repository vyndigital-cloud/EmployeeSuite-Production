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

    // 2026 COMPLIANT: Use App Bridge navigation instead of window.location
    async function navigateAuthenticated(url) {
        try {
            // Get fresh session token
            const token = await window.shopify.idToken();

            // OPTION 1: Use App Bridge navigate (preferred - 2026 compliant)
            if (window.shopify.navigate) {
                // Extract path from full URL
                const urlObj = new URL(url, window.location.origin);
                const path = urlObj.pathname + urlObj.search;

                // App Bridge automatically injects token
                window.shopify.navigate(path);
                console.log('[Auth Nav 2026] App Bridge navigation:', path);
            }
            // OPTION 2: Fallback to manual token append (legacy support)
            else {
                const urlObj = new URL(url, window.location.origin);
                urlObj.searchParams.set('id_token', token);
                window.location.href = urlObj.toString();
                console.log('[Auth Nav 2026] Legacy fallback:', urlObj.toString());
            }
        } catch (error) {
            console.error('[Auth Nav 2026] Token fetch failed:', error);
            // Last resort fallback
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

        console.log('[Auth Nav 2026] ✅ Navigation uses App Bridge 4.0 (no window.location)');
    });

    // Expose for manual use
    window.navigateAuthenticated = navigateAuthenticated;
})();
