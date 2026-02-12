// HYDRA STATE MANAGER - Pinnacle Lockdown
// DNA Persistence + Pre-Emptive Auth + Self-Healing DOM
// Sentinel Bot - Maximum Diagnostic Client with Proactive Shield
// Mimics user behavior to detect App Bridge initialization failures

const Sentinel = {
    logs: [],
    startTime: Date.now(),
    domLoadTime: null,
    appBridgeReadyTime: null,
    stateSnapshots: [],
    requestFailures: [],
    currentShop: null,
    currentHost: null,

    // HYDRA: DNA Vault
    dnaVault: {
        shop: null,
        host: null,
        sessionToken: null,
        tokenExpiry: null,
        lastRefresh: null
    },

    silentPulseInterval: null,

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

    // ==================== DNA PERSISTENCE ====================

    // Save DNA to dual storage (sessionStorage + indexedDB)
    async saveDNA(shop, host, sessionToken) {
        const dna = {
            shop,
            host,
            sessionToken,
            tokenExpiry: Date.now() + (5 * 60 * 1000), // 5 minutes
            lastRefresh: Date.now()
        };

        // Save to memory
        this.dnaVault = dna;
        this.currentShop = shop;
        this.currentHost = host;

        // Save to sessionStorage
        sessionStorage.setItem('dna_vault', JSON.stringify(dna));

        // Save to indexedDB for persistence across tabs
        try {
            await this.saveToIndexedDB(dna);
        } catch (error) {
            this.log('⚠️ IndexedDB save failed, using sessionStorage only', { error: error.message });
        }

        this.log('🧬 DNA saved to vault', {
            shop,
            host,
            tokenExpiry: new Date(dna.tokenExpiry).toISOString()
        });
    },

    // Load DNA from vault (indexedDB → sessionStorage → URL params)
    async loadDNA() {
        // Try indexedDB first
        try {
            const dbDNA = await this.loadFromIndexedDB();
            if (dbDNA && dbDNA.shop) {
                this.dnaVault = dbDNA;
                this.currentShop = dbDNA.shop;
                this.currentHost = dbDNA.host;
                this.log('🧬 DNA loaded from indexedDB', { shop: dbDNA.shop });
                return dbDNA;
            }
        } catch (error) {
            this.log('⚠️ IndexedDB load failed', { error: error.message });
        }

        // Fallback to sessionStorage
        const sessionDNA = sessionStorage.getItem('dna_vault');
        if (sessionDNA) {
            try {
                const dna = JSON.parse(sessionDNA);
                this.dnaVault = dna;
                this.currentShop = dna.shop;
                this.currentHost = dna.host;
                this.log('🧬 DNA loaded from sessionStorage', { shop: dna.shop });
                return dna;
            } catch (error) {
                this.log('⚠️ SessionStorage parse failed', { error: error.message });
            }
        }

        // Fallback to URL params
        const urlParams = new URLSearchParams(window.location.search);
        const shop = urlParams.get('shop');
        const host = urlParams.get('host');

        if (shop && host) {
            this.log('🧬 DNA loaded from URL params', { shop, host });
            // Save for future use
            await this.saveDNA(shop, host, null);
            return { shop, host };
        }

        this.log('❌ No DNA found - shark imminent!');
        return null;
    },

    // IndexedDB helpers
    async saveToIndexedDB(dna) {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('SentinelDB', 1);

            request.onerror = () => reject(request.error);
            request.onsuccess = (event) => {
                const db = event.target.result;
                const transaction = db.transaction(['dna'], 'readwrite');
                const store = transaction.objectStore('dna');
                store.put({ id: 1, ...dna });
                transaction.oncomplete = () => resolve();
                transaction.onerror = () => reject(transaction.error);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains('dna')) {
                    db.createObjectStore('dna', { keyPath: 'id' });
                }
            };
        });
    },

    async loadFromIndexedDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('SentinelDB', 1);

            request.onerror = () => reject(request.error);
            request.onsuccess = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains('dna')) {
                    resolve(null);
                    return;
                }
                const transaction = db.transaction(['dna'], 'readonly');
                const store = transaction.objectStore('dna');
                const getRequest = store.get(1);
                getRequest.onsuccess = () => resolve(getRequest.result);
                getRequest.onerror = () => reject(getRequest.error);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains('dna')) {
                    db.createObjectStore('dna', { keyPath: 'id' });
                }
            };
        });
    },

    // ==================== PRE-EMPTIVE AUTH BRIDGE ====================

    // Get valid token with cache-first strategy
    async getValidToken() {
        // Check if cached token is still valid (>30s remaining)
        const now = Date.now();
        const timeRemaining = this.dnaVault.tokenExpiry - now;

        if (this.dnaVault.sessionToken && timeRemaining > 30000) {
            this.log('✅ Using cached token', {
                timeRemaining: Math.floor(timeRemaining / 1000) + 's'
            });
            return this.dnaVault.sessionToken;
        }

        // Token expired or about to expire - refresh in background
        this.log('🔄 Token expired or expiring soon - refreshing', {
            expired: timeRemaining <= 0,
            timeRemaining: Math.floor(timeRemaining / 1000) + 's'
        });

        return await this.refreshTokenBackground();
    },

    // Background token refresh
    async refreshTokenBackground() {
        try {
            if (!window.shopify || typeof window.shopify.idToken !== 'function') {
                throw new Error('App Bridge not available');
            }

            const startTime = Date.now();
            const token = await window.shopify.idToken();
            const elapsed = Date.now() - startTime;

            if (token) {
                await this.saveDNA(this.dnaVault.shop, this.dnaVault.host, token);
                this.log('✅ Background token refresh complete', {
                    latency_ms: elapsed,
                    type: 'Background Refresh'
                });
                return token;
            }

            throw new Error('No token returned');
        } catch (error) {
            this.log('❌ Background token refresh failed', { error: error.message });
            return null;
        }
    },

    // Silent Pulse: Refresh token every 4 minutes
    startSilentPulse() {
        // Refresh every 4 minutes (240 seconds)
        this.silentPulseInterval = setInterval(async () => {
            this.log('💓 Silent Pulse: Starting background refresh');

            try {
                const token = await this.refreshTokenBackground();

                // Send heartbeat to backend
                if (token && this.dnaVault.shop) {
                    await fetch('/telemetry/heartbeat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            shop: this.dnaVault.shop,
                            status: 'verified',
                            token_preview: token.substring(0, 10)
                        })
                    });
                    this.log('💓 Heartbeat sent to Mission Control');
                }
            } catch (error) {
                this.log('❌ Silent Pulse failed', { error: error.message });

                // Send failed heartbeat
                if (this.dnaVault.shop) {
                    await fetch('/telemetry/heartbeat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            shop: this.dnaVault.shop,
                            status: 'failed',
                            error: error.message
                        })
                    });
                }
            }
        }, 4 * 60 * 1000);

        this.log('💓 Silent Pulse started - refreshing every 4 minutes');
    },

    stopSilentPulse() {
        if (this.silentPulseInterval) {
            clearInterval(this.silentPulseInterval);
            this.silentPulseInterval = null;
            this.log('💓 Silent Pulse stopped');
        }
    },

    // PROACTIVE SHIELD: Track shop/host in sessionStorage
    initSessionTracking() {
        const urlParams = new URLSearchParams(window.location.search);
        const shop = urlParams.get('shop');
        const host = urlParams.get('host');

        if (shop) {
            sessionStorage.setItem('currentShop', shop);
            this.currentShop = shop;
        } else {
            this.currentShop = sessionStorage.getItem('currentShop');
        }

        if (host) {
            sessionStorage.setItem('currentHost', host);
            this.currentHost = host;
        } else {
            this.currentHost = sessionStorage.getItem('currentHost');
        }

        this.log('🛡️ Session tracking initialized', {
            shop: this.currentShop,
            host: this.currentHost
        });
    },

    // LINK PROXY: Intercept all clicks and ensure params
    initLinkProxy() {
        document.addEventListener('click', (event) => {
            const link = event.target.closest('a');

            if (!link || !link.href) return;

            // Only intercept internal links
            if (!link.href.startsWith(window.location.origin)) return;

            // Skip if already has shop/host or is external
            const linkUrl = new URL(link.href);

            // Append from sessionStorage if missing
            if (this.currentShop && !linkUrl.searchParams.has('shop')) {
                linkUrl.searchParams.set('shop', this.currentShop);
                event.preventDefault();

                this.log('🛡️ Link Proxy: Injected shop parameter', {
                    originalHref: link.href,
                    shop: this.currentShop
                });

                link.href = linkUrl.toString();
                link.click();
                return;
            }

            if (this.currentHost && !linkUrl.searchParams.has('host')) {
                linkUrl.searchParams.set('host', this.currentHost);
                event.preventDefault();

                this.log('🛡️ Link Proxy: Injected host parameter', {
                    originalHref: link.href,
                    host: this.currentHost
                });

                link.href = linkUrl.toString();
                link.click();
                return;
            }
        }, true); // Capture phase

        this.log('🛡️ Link Proxy: Active - protecting all navigation');
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

    // NETWORK INTERCEPTOR: Verify internal links + Telemetry Push
    async testInternalLink(url) {
        try {
            const response = await fetch(url, {
                method: 'HEAD',
                mode: 'same-origin'
            });

            if (response.status !== 200) {
                const failureData = {
                    url,
                    status: response.status,
                    statusText: response.statusText,
                    level: 'CRITICAL',
                    sourcePage: window.location.href
                };

                this.log('❌ CRITICAL: Internal link returned non-200', failureData);

                // TELEMETRY PUSH: Send to backend with source page
                await this.sendTelemetryPush({
                    event_type: 'LINK_VALIDATION_FAILURE',
                    broken_path: url,
                    source_page: window.location.href,
                    ...failureData
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

    // Dedicated telemetry push for broken links
    async sendTelemetryPush(data) {
        try {
            await fetch('/telemetry/log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: 'SENTINEL_LINK_SCOUT',
                    timestamp: new Date().toISOString(),
                    level: 'CRITICAL',
                    ...data
                })
            });
            this.log('📤 Telemetry pushed for broken link');
        } catch (error) {
            console.error('[Sentinel 🤖] Failed to push telemetry:', error);
        }
    },

    // ==================== SELF-HEALING DOM ====================

    // SentinelScout: Shadow-fetch and heal broken links
    async initSentinelScout() {
        // Scan existing links
        await this.scoutAllLinks();

        // Watch for new links with MutationObserver
        const observer = new MutationObserver(async (mutations) => {
            for (const mutation of mutations) {
                for (const node of mutation.addedNodes) {
                    if (node.nodeName === 'A') {
                        await this.scoutLink(node);
                    } else if (node.querySelectorAll) {
                        const links = node.querySelectorAll('a');
                        for (const link of links) {
                            await this.scoutLink(link);
                        }
                    }
                }
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        this.log('🔍 SentinelScout: Watching for broken links');
    },

    async scoutAllLinks() {
        const links = document.querySelectorAll('a[href]');
        let scoutedCount = 0;

        for (const link of links) {
            if (link.href.startsWith(window.location.origin)) {
                await this.scoutLink(link);
                scoutedCount++;
            }
        }

        this.log(`🔍 SentinelScout: Scanned ${scoutedCount} internal links`);
    },

    async scoutLink(link) {
        if (!link.href || !link.href.startsWith(window.location.origin)) {
            return;
        }

        // Skip already scouted links
        if (link.dataset.scouted === 'true') {
            return;
        }

        try {
            const response = await fetch(link.href, {
                method: 'HEAD',
                mode: 'same-origin'
            });

            if (response.status === 404) {
                // GHOST 404 CORRECTION: Redirect to dashboard
                const originalHref = link.href;
                link.href = '/home'; // Highest-converting route
                link.dataset.healed = 'true';

                this.log('🩹 Self-Healing DOM: 404 link corrected', {
                    originalHref,
                    newHref: link.href
                });

                // Send telemetry
                await this.sendTelemetryPush({
                    event_type: '404_LINK_HEALED',
                    broken_path: originalHref,
                    healed_path: link.href,
                    source_page: window.location.href
                });
            }

            link.dataset.scouted = 'true';
        } catch (error) {
            // Network error - hide link to prevent user confusion
            link.style.display = 'none';
            link.dataset.hidden = 'true';

            this.log('🩹 Self-Healing DOM: Broken link hidden', {
                href: link.href,
                error: error.message
            });
        }
    },

    // ==================== GLOBAL PROXY ====================

    // Wrap XMLHttpRequest and fetch to auto-inject DNA headers
    initGlobalProxy() {
        const sentinel = this;

        // Wrap fetch
        const originalFetch = window.fetch;
        window.fetch = async function (...args) {
            const [url, options = {}] = args;

            // Only modify internal requests
            const urlString = typeof url === 'string' ? url : url.url;
            if (urlString && !urlString.startsWith('http')) {
                // It's a relative URL - inject DNA
                options.headers = options.headers || {};

                if (sentinel.dnaVault.shop) {
                    options.headers['X-Shopify-Shop-Domain'] = sentinel.dnaVault.shop;
                }

                if (sentinel.dnaVault.host) {
                    options.headers['X-Shopify-Host'] = sentinel.dnaVault.host;
                }

                // Get fresh token
                const token = await sentinel.getValidToken();
                if (token) {
                    options.headers['Authorization'] = `Bearer ${token}`;
                }

                sentinel.log('🌐 Global Proxy: DNA injected into fetch', {
                    url: urlString,
                    hasShop: !!sentinel.dnaVault.shop,
                    hasHost: !!sentinel.dnaVault.host,
                    hasToken: !!token
                });

                args[1] = options;
            }

            return originalFetch.apply(this, args);
        };

        // Wrap XMLHttpRequest
        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function (method, url, ...rest) {
            this._sentinel_url = url;
            this._sentinel_method = method;
            return originalOpen.call(this, method, url, ...rest);
        };

        XMLHttpRequest.prototype.send = async function (body) {
            // Only modify internal requests
            if (this._sentinel_url && !this._sentinel_url.startsWith('http')) {
                if (sentinel.dnaVault.shop) {
                    this.setRequestHeader('X-Shopify-Shop-Domain', sentinel.dnaVault.shop);
                }

                if (sentinel.dnaVault.host) {
                    this.setRequestHeader('X-Shopify-Host', sentinel.dnaVault.host);
                }

                // Get fresh token
                const token = await sentinel.getValidToken();
                if (token) {
                    this.setRequestHeader('Authorization', `Bearer ${token}`);
                }

                sentinel.log('🌐 Global Proxy: DNA injected into XHR', {
                    method: this._sentinel_method,
                    url: this._sentinel_url,
                    hasShop: !!sentinel.dnaVault.shop,
                    hasHost: !!sentinel.dnaVault.host,
                    hasToken: !!token
                });
            }

            return originalSend.call(this, body);
        };

        this.log('🌐 Global Proxy: Active - auto-injecting DNA headers');
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
    },

    // LAYER 1: MUTATION OBSERVER - Watch for dynamically added links
    initMutationObserver() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    // Check if node is a link or contains links
                    if (node.nodeName === 'A') {
                        this.contextInjector(node);
                    } else if (node.querySelectorAll) {
                        const links = node.querySelectorAll('a');
                        links.forEach(link => this.contextInjector(link));
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        this.log('🔍 MutationObserver: Watching for dynamic links');
    },

    // Context injector for new links
    contextInjector(link) {
        // Only inject for internal links
        if (!link.href || !link.href.startsWith(window.location.origin)) {
            return;
        }

        // Ensure shop and host params are present
        const urlParams = new URLSearchParams(window.location.search);
        const shop = urlParams.get('shop');
        const host = urlParams.get('host');

        if (shop && host) {
            try {
                const linkUrl = new URL(link.href);
                if (!linkUrl.searchParams.has('shop')) {
                    linkUrl.searchParams.set('shop', shop);
                }
                if (!linkUrl.searchParams.has('host')) {
                    linkUrl.searchParams.set('host', host);
                }
                link.href = linkUrl.toString();

                this.log('🔧 Context injected into dynamic link', {
                    originalHref: link.getAttribute('href'),
                    newHref: link.href
                });
            } catch (error) {
                this.log('❌ Failed to inject context', { error: error.message });
            }
        }
    },

    // LAYER 2: REQUEST INTERCEPTOR - Wrap fetch for 401/404 detection
    initFetchInterceptor() {
        const originalFetch = window.fetch;
        const sentinel = this;

        window.fetch = async function (...args) {
            const [url, options] = args;

            try {
                const response = await originalFetch.apply(this, args);

                // Capture 401 or 404 failures
                if (response.status === 401 || response.status === 404) {
                    const failureData = {
                        url: typeof url === 'string' ? url : url.url,
                        status: response.status,
                        statusText: response.statusText,
                        method: options?.method || 'GET',
                        timestamp: new Date().toISOString(),
                        // Full state snapshot
                        state: {
                            params: Object.fromEntries(new URLSearchParams(window.location.search)),
                            headers: options?.headers || {},
                            localStorage: sentinel.captureLocalStorage(),
                            cookies: document.cookie,
                            referrer: document.referrer
                        }
                    };

                    sentinel.requestFailures.push(failureData);

                    sentinel.log(`❌ CRITICAL: Fetch ${response.status} detected`, failureData);

                    // Send immediately to backend
                    await sentinel.sendCriticalEvent({
                        event_type: 'FETCH_FAILURE',
                        ...failureData
                    });
                }

                return response;
            } catch (error) {
                sentinel.log('❌ CRITICAL: Fetch error', {
                    url: typeof url === 'string' ? url : url.url,
                    error: error.message
                });
                throw error;
            }
        };

        this.log('🌐 Fetch Interceptor: Monitoring all requests');
    },

    // Capture localStorage safely
    captureLocalStorage() {
        try {
            const storage = {};
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                storage[key] = localStorage.getItem(key);
            }
            return storage;
        } catch (error) {
            return { error: 'localStorage not accessible' };
        }
    },

    // LAYER 3: APP BRIDGE SPEED-TRAP
    initAppBridgeSpeedTrap() {
        // Record DOM load time
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.domLoadTime = Date.now();
                this.log('📍 DOMContentLoaded fired', {
                    elapsed_ms: this.domLoadTime - this.startTime
                });
                this.checkAppBridgeSpeed();
            });
        } else {
            this.domLoadTime = Date.now();
            this.checkAppBridgeSpeed();
        }
    },

    async checkAppBridgeSpeed() {
        const start = this.domLoadTime || Date.now();
        let ready = false;
        let attempts = 0;

        while (!ready && attempts < 50) {
            ready = !!(window.shopify && window['app-bridge']);
            if (!ready) {
                await new Promise(resolve => setTimeout(resolve, 100));
                attempts++;
            }
        }

        this.appBridgeReadyTime = Date.now();
        const latency = this.appBridgeReadyTime - start;

        if (latency > 1500) {
            this.log('🚨 PERFORMANCE BOTTLENECK: App Bridge exceeded 1500ms', {
                latency_ms: latency,
                threshold_ms: 1500,
                level: 'WARNING'
            });

            await this.sendCriticalEvent({
                event_type: 'APP_BRIDGE_SLOW',
                latency_ms: latency,
                threshold_ms: 1500,
                dom_to_ready: latency
            });
        } else {
            this.log(`⚡ App Bridge ready in ${latency}ms (under threshold)`);
        },

        // ==================== RESOURCE ERROR RECOVERY ====================

        // Sentinel Recovery: Catch failed scripts/images
        initResourceRecovery() {
            window.addEventListener('error', async (event) => {
                // Only handle resource errors
                if (!event.target || (!event.target.tagName)) return;

                const tag = event.target.tagName;
                if (tag === 'IMG' || tag === 'SCRIPT' || tag === 'LINK') {
                    const resource = event.target.src || event.target.href || 'unknown';

                    this.log('🛡️ Sentinel Recovery: Resource failed to load', {
                        type: tag,
                        resource,
                        level: 'WARNING'
                    });

                    // Send error recovery telemetry
                    if (this.dnaVault.shop) {
                        try {
                            await fetch('/telemetry/error_recovery', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    type: 'resource_fail',
                                    shop: this.dnaVault.shop,
                                    resource,
                                    tag,
                                    page: window.location.href
            setTimeout(() => Sentinel.performWalkthrough(), 500);
        });
} else {
    (async () => {
        await Sentinel.initAllLayers();
        setTimeout(() => Sentinel.performWalkthrough(), 500);
    })();
}

// Expose for manual debugging
window.Sentinel = Sentinel;
