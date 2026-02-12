// Sentinel Bot - Automated Diagnostic Client
// Mimics user behavior to detect App Bridge initialization failures

const Sentinel = {
    logs: [],
    startTime: Date.now(),

    log(message, data = {}) {
        const entry = {
            timestamp: new Date().toISOString(),
            elapsed_ms: Date.now() - this.startTime,
            message,
            ...data
        };
        this.logs.push(entry);
        console.log(`[Sentinel 🤖] ${message}`, data);
    },

    async checkAppBridge() {
        const hasShopify = !!window.shopify;
        const hasAppBridge = !!window['app-bridge'];
        const hasIdToken = !!(window.shopify && typeof window.shopify.idToken === 'function');

        this.log("App Bridge State Check", {
            hasShopify,
            hasAppBridge,
            hasIdToken,
            isReady: hasShopify && hasAppBridge && hasIdToken
        });

        return hasShopify && hasAppBridge && hasIdToken;
    },

    async performWalkthrough() {
        this.log("🚀 Starting Sentinel Walkthrough");

        // Step 1: Initial state check
        await new Promise(resolve => setTimeout(resolve, 100));
        const initialReady = await this.checkAppBridge();

        // Step 2: Check for protected links
        const settingsLinks = document.querySelectorAll('a[data-auth-required="true"][href*="settings"]');
        const subscribeLinks = document.querySelectorAll('a[data-auth-required="true"][href*="subscribe"]');

        this.log("Protected Links Found", {
            settingsCount: settingsLinks.length,
            subscribeCount: subscribeLinks.length,
            totalProtected: settingsLinks.length + subscribeLinks.length
        });

        // Step 3: Wait for App Bridge (max 5 seconds)
        let attempts = 0;
        while (!await this.checkAppBridge() && attempts < 50) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }

        if (attempts >= 50) {
            this.log("❌ CRITICAL: App Bridge failed to initialize within 5 seconds");
        } else {
            this.log(`✅ App Bridge ready after ${attempts * 100}ms`);
        }

        // Step 4: Test click interception
        if (settingsLinks.length > 0) {
            const link = settingsLinks[0];
            this.log("Testing Settings link click", {
                href: link.href,
                hasDataAttr: link.hasAttribute('data-auth-required')
            });

            // Simulate click without actually navigating
            const clickEvent = new MouseEvent('click', {
                bubbles: true,
                cancelable: true,
                view: window
            });

            const prevented = !link.dispatchEvent(clickEvent);
            this.log("Click Test Result", {
                wasPreventDefault: prevented,
                appBridgeReady: !!window.shopify
            });
        }

        // Step 5: Check body ready state
        const bodyHasClass = document.body.classList.contains('app-ready');
        this.log("Body Ready State", {
            hasAppReadyClass: bodyHasClass,
            bodyOpacity: window.getComputedStyle(document.body).opacity
        });

        // Final report
        await this.report();
    },

    async report() {
        const summary = {
            user_id: 'SENTINEL_BOT',
            timestamp: new Date().toISOString(),
            total_elapsed_ms: Date.now() - this.startTime,
            events: this.logs,
            environment: {
                userAgent: navigator.userAgent,
                url: window.location.href,
                referrer: document.referrer,
                screenSize: `${window.screen.width}x${window.screen.height}`
            }
        };

        this.log("📤 Sending report to backend", {
            totalEvents: this.logs.length,
            totalTime: summary.total_elapsed_ms
        });

        try {
            const response = await fetch('/client-telemetry/log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(summary)
            });

            if (response.ok) {
                console.log('[Sentinel 🤖] ✅ Report sent successfully');
            } else {
                console.error('[Sentinel 🤖] ❌ Report failed:', response.status);
            }
        } catch (error) {
            console.error('[Sentinel 🤖] ❌ Report error:', error);
        }
    }
};

// Auto-start walkthrough after DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => Sentinel.performWalkthrough(), 500);
    });
} else {
    setTimeout(() => Sentinel.performWalkthrough(), 500);
}

// Expose for manual debugging
window.Sentinel = Sentinel;
