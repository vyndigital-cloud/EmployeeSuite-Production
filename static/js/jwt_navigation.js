/**
 * GOLDEN PATH: JWT Navigation Wrapper (Option B)
 * Appends JWT token to navigation URLs for Settings and Billing links
 */

document.addEventListener('DOMContentLoaded', function () {
    // Get session token from Shopify App Bridge
    async function getSessionToken() {
        try {
            if (window.shopify && typeof window.shopify.idToken === 'function') {
                return await window.shopify.idToken();
            }
        } catch (e) {
            console.error("Failed to get session token:", e);
        }
        return null;
    }

    // Navigate with JWT token appended
    async function navigateWithAuth(url) {
        try {
            const token = await getSessionToken();
            if (token) {
                const fullUrl = new URL(url, window.location.origin);
                fullUrl.searchParams.set('id_token', token);
                console.log('✅ Navigating with JWT:', fullUrl.pathname);
                window.location.href = fullUrl.toString();
            } else {
                // No JWT available - will trigger backend alert
                console.warn('⚠️ JWT not available for navigation to:', url);
                window.location.href = url;
            }
        } catch (error) {
            console.error('❌ navigateWithAuth failed:', error);
            window.location.href = url; // Fallback
        }
    }

    // Intercept all links marked with data-auth-required="true"
    const authLinks = document.querySelectorAll('a[data-auth-required="true"]');
    authLinks.forEach(function (link) {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            navigateWithAuth(this.href);
        });
    });

    if (authLinks.length > 0) {
        console.log(`✅ JWT Navigation Interceptor: Protecting ${authLinks.length} link(s)`);
    }
});
