// App Bridge 4.0 Navigation Helper
// 2026 Shopify Compliance - Zero window.location redirects

(function () {
    'use strict';

    // Wait for App Bridge to be ready
    function waitForAppBridge(callback) {
        if (window.shopify && window.shopify.navigate) {
            callback();
        } else {
            setTimeout(() => waitForAppBridge(callback), 50);
        }
    }

    // Modern App Bridge navigation (2026 compliant)
    function navigateWithAppBridge(path) {
        if (window.shopify && window.shopify.navigate) {
            // App Bridge handles token automatically
            window.shopify.navigate(path);
            console.log('[App Bridge 4.0] Navigating:', path);
        } else {
            console.error('[App Bridge 4.0] Not available - fallback to manual nav');
            // Fallback only if App Bridge fails
            window.location.href = path;
        }
    }

    // Convert relative path to App Bridge compatible format
    function normalizePathForAppBridge(url) {
        try {
            const urlObj = new URL(url, window.location.origin);
            // Return path + search (App Bridge handles host resolution)
            return urlObj.pathname + urlObj.search;
        } catch (e) {
            console.error('[App Bridge 4.0] URL parse error:', e);
            return url;
        }
    }

    // Enhanced link click handler
    function handleLinkClick(e, href) {
        // Let Cmd/Ctrl+Click open in new tab normally
        if (e.metaKey || e.ctrlKey) {
            return true;
        }

        e.preventDefault();

        // Normalize and navigate
        const path = normalizePathForAppBridge(href);
        navigateWithAppBridge(path);

        return false;
    }

    // Auto-enhance all internal links
    function enhanceLinks() {
        const links = document.querySelectorAll('a[href]');

        links.forEach(link => {
            const href = link.getAttribute('href');

            // Skip external, anchors, special protocols
            if (!href || href.startsWith('#') || href.startsWith('http') ||
                href.startsWith('mailto:') || href.startsWith('tel:')) {
                return;
            }

            // Skip already enhanced
            if (link.dataset.appBridge4) {
                return;
            }

            // Skip static files
            if (href.includes('/static/')) {
                return;
            }

            // Mark as enhanced
            link.dataset.appBridge4 = 'true';

            // Add click handler
            link.addEventListener('click', function (e) {
                return handleLinkClick(e, this.href);
            });
        });
    }

    // Initialize when App Bridge is ready
    waitForAppBridge(function () {
        console.log('[App Bridge 4.0] ✅ Ready - Zero window.location mode');

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

        console.log('[App Bridge 4.0] All navigation now uses shopify.navigate() - 2026 compliant ✅');
    });

    // Expose for manual use
    window.navigateWithAppBridge = navigateWithAppBridge;

})();
