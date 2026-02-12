// Sentinel Bot - Enhanced Diagnostic Client
// Mimics user behavior to detect App Bridge initialization failures

const Sentinel = {
    logs: [],
    startTime: Date.now(),
    stateSnapshots: [],

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

    // STATE SNAPSHOT: Track shop/host parameters
    captureStateSnapshot(context = 'unknown') {
        const urlParams = new URLSearchParams(window.location.search);
        const snapshot = {
            context,
            timestamp: new Date().toISOString(),
            elapsed_ms: Date.now() - this.startTime,
            url: window.location.href,
            shop: urlParams.get('shop') || 'MISSING',
            host: urlParams.get('host') || 'MISSING',
            hasIdToken: urlParams.has('id_token')
        };

        this.stateSnapshots.push(snapshot);

        // SHARK OF GLASS DETECTION: Missing shop/host
        if (!urlParams.has('shop') || !urlParams.has('host')) {
            this.log('🦈 SHARK OF GLASS DETECTED: shop/host parameters missing!', {
                context,
                shop: snapshot.shop,
                host: snapshot.host,
                url: window.location.href
            });
        }

        return snapshot;
    },

    // NETWORK INTERCEPTOR: Verify internal links
    async testInternalLink(url) {
        try {
            const response = await fetch(url, {
                method: 'HEAD',
                mode: 'same-origin'
            });

            if (response.status !== 200) {
                this.log('❌ CRITICAL: Internal link returned non-200', {
                    url,
                    status: response.status,
                    statusText: response.statusText,
                    level: 'CRITICAL'
                });

                // Send to backend immediately
                await this.sendCriticalEvent({
                    event_type: 'LINK_VALIDATION_FAILURE',
                    url,
                    status: response.status,
                    statusText: response.statusText
                });
            }

            return response.status === 200;
        } catch (error) {
            this.log('❌ CRITICAL: Link test failed', {
                url,
                error: error.message,
                level: 'CRITICAL'
            });
            return false;
        }
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

    // BULLET-PROOF LOOP: Comprehensive validation
    async bulletProofLoop() {
        this.log("🔫 Starting Bullet-Proof Loop");

        // 1. Scan all links on load
        const allLinks = document.querySelectorAll('a[href]');
        const internalLinks = Array.from(allLinks).filter(link =>
            link.href.startsWith(window.location.origin)
        );
        const protectedLinks = document.querySelectorAll('a[data-auth-required="true"]');

        this.log("Link Scan Complete", {
            totalLinks: allLinks.length,
            internalLinks: internalLinks.length,
            protectedLinks: protectedLinks.length
        });

        // 2. Verify App Bridge status with timeout
        const appBridgeStart = Date.now();
        let appBridgeReady = false;
        let attempts = 0;

        while (!appBridgeReady && attempts < 50) {
            appBridgeReady = await this.checkAppBridge();
            if (!appBridgeReady) {
                await new Promise(resolve => setTimeout(resolve, 100));
                attempts++;
            }
        }

        const appBridgeLatency = Date.now() - appBridgeStart;

        // 3. Report latency over 1500ms
        if (appBridgeLatency > 1500) {
            this.log('⚠️ WARNING: App Bridge initialization exceeded 1500ms', {
                latency_ms: appBridgeLatency,
                level: 'WARNING'
            });

            await this.sendCriticalEvent({
                event_type: 'APP_BRIDGE_LATENCY',
                latency_ms: appBridgeLatency,
                threshold_ms: 1500
            });
        } else if (appBridgeReady) {
            this.log(`✅ App Bridge ready in ${appBridgeLatency}ms`);
        } else {
            this.log('❌ CRITICAL: App Bridge failed to initialize', {
                latency_ms: appBridgeLatency,
                level: 'CRITICAL'
            });
        }

        return {
            linksScanned: allLinks.length,
            appBridgeLatency,
            appBridgeReady
        };
    },

    async performWalkthrough() {
        this.log("🚀 Starting Enhanced Sentinel Walkthrough");

        // STATE SNAPSHOT: Initial state
        this.captureStateSnapshot('walkthrough_start');

        // BULLET-PROOF LOOP
        const loopResults = await this.bulletProofLoop();

        // STATE SNAPSHOT: After App Bridge check
        this.captureStateSnapshot('post_app_bridge_check');

        // Step: Check for protected links
        const settingsLinks = document.querySelectorAll('a[data-auth-required="true"][href*="settings"]');
        const subscribeLinks = document.querySelectorAll('a[data-auth-required="true"][href*="subscribe"]');

        this.log("Protected Links Found", {
            settingsCount: settingsLinks.length,
            subscribeCount: subscribeLinks.length,
            totalProtected: settingsLinks.length + subscribeLinks.length
        });

        // NETWORK INTERCEPTOR: Test a few critical links
        if (settingsLinks.length > 0) {
            const testLink = settingsLinks[0].href;
            this.log("Testing Settings link", { url: testLink });
            await this.testInternalLink(testLink);
        }

        // Step: Test click interception
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

        // STATE SNAPSHOT: Final state
        this.captureStateSnapshot('walkthrough_end');

        // Step: Check body ready state
        const bodyHasClass = document.body.classList.contains('app-ready');
        this.log("Body Ready State", {
            hasAppReadyClass: bodyHasClass,
            bodyOpacity: window.getComputedStyle(document.body).opacity
        });

        // Final report
        await this.report();
    },

    async sendCriticalEvent(eventData) {
        try {
            await fetch('/client-telemetry/log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: 'SENTINEL_BOT_CRITICAL',
                    timestamp: new Date().toISOString(),
                    level: 'CRITICAL',
                    event: eventData
                })
            });
        } catch (error) {
            console.error('[Sentinel 🤖] Failed to send critical event:', error);
        }
    },

    async report() {
        const summary = {
            user_id: 'SENTINEL_BOT',
            timestamp: new Date().toISOString(),
            total_elapsed_ms: Date.now() - this.startTime,
            events: this.logs,
            state_snapshots: this.stateSnapshots,
            environment: {
                userAgent: navigator.userAgent,
                url: window.location.href,
                referrer: document.referrer || '(none)',  // Track iframe escapes
                screenSize: `${window.screen.width}x${window.screen.height}`,
                isIframe: window.self !== window.top,
                hasShopParam: new URLSearchParams(window.location.search).has('shop'),
                hasHostParam: new URLSearchParams(window.location.search).has('host')
            }
        };

        // Log referrer explicitly for iframe escape detection
        if (document.referrer.includes('admin.shopify.com')) {
            this.log('🦈 SHARK DETECTED: Referrer is admin.shopify.com - iframe escape confirmed');
        }

        this.log("📤 Sending report to backend", {
            totalEvents: this.logs.length,
            totalSnapshots: this.stateSnapshots.length,
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
