// App Bridge Authenticated Navigation Helper
// Ensures all internal navigation preserves session token

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

    // Authenticated navigation using App Bridge
    async function navigateAuthenticated(url) {
        try {
            // Get fresh session token
            const token = await window.shopify.idToken();

            // Append token to URL
            const urlObj = new URL(url, window.location.origin);
            urlObj.searchParams.set('id_token', token);

            // Navigate with token
            window.location.href = urlObj.toString();
        } catch (error) {
            console.error('[Auth Nav] Token fetch failed:', error);
            // Fallback to regular navigation
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

                console.log('[Auth Nav] Navigating with session token:', targetUrl);
                navigateAuthenticated(targetUrl);
            });
        });
    }

    // Initialize when App Bridge is ready
    waitForAppBridge(function () {
        console.log('[Auth Nav] App Bridge ready - enhancing links');

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

        console.log('[Auth Nav] ✅ All internal navigation will preserve session tokens');
    });

    // Expose for manual use
    window.navigateAuthenticated = navigateAuthenticated;
})();
