"""
App Bridge Navigation - Shopify Best Practices
Implements proper navigation for embedded Shopify apps using App Bridge
"""

def get_app_bridge_navigation_js():
    """
    Get JavaScript for App Bridge navigation
    """
    return """
<script>
// App Bridge Navigation Manager
class AppBridgeNavigation {
    constructor() {
        this.app = null;
        this.isEmbedded = false;
        this.init();
    }
    
    init() {
        // Check if we're in an embedded context
        const urlParams = new URLSearchParams(window.location.search);
        const host = urlParams.get('host');
        this.isEmbedded = !!host;
        
        if (this.isEmbedded && window.shopify) {
            this.app = window.shopify.app;
            console.log('App Bridge navigation initialized');
        }
    }
    
    // Navigate to a new route
    navigate(path, options = {}) {
        const url = this.buildUrl(path, options);
        
        if (this.isEmbedded && this.app) {
            // Use App Bridge for embedded navigation
            this.app.dispatch(window.shopify.Action.REDIRECT, {
                path: path,
                newContext: options.newContext || false
            });
        } else {
            // Fallback for standalone
            window.location.href = url;
        }
    }
    
    // Navigate with loading state
    navigateWithLoading(path, loadingMessage = 'Loading...') {
        this.showLoading(loadingMessage);
        
        // Add small delay for better UX
        setTimeout(() => {
            this.navigate(path);
        }, 300);
    }
    
    // Open in new tab
    openNewTab(url) {
        if (this.isEmbedded && this.app) {
            this.app.dispatch(window.shopify.Action.OPEN, {
                url: url
            });
        } else {
            window.open(url, '_blank');
        }
    }
    
    // Show modal
    showModal(title, content, options = {}) {
        if (this.isEmbedded && this.app) {
            this.app.dispatch(window.shopify.Action.MODAL, {
                title: title,
                message: content,
                footer: options.footer,
                size: options.size || 'large'
            });
        } else {
            // Fallback to browser alert/modal
            alert(`${title}: ${content}`);
        }
    }
    
    // Show toast notification
    showToast(message, options = {}) {
        if (this.isEmbedded && this.app) {
            this.app.dispatch(window.shopify.Action.TOAST, {
                message: message,
                duration: options.duration || 5000,
                isError: options.isError || false
            });
        } else {
            // Fallback to console/log
            console.log(`Toast: ${message}`);
        }
    }
    
    // Show loading overlay
    showLoading(message = 'Loading...') {
        const overlay = document.createElement('div');
        overlay.id = 'app-bridge-loading';
        overlay.innerHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(255, 255, 255, 0.9);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            ">
                <div style="text-align: center;">
                    <div style="
                        width: 40px;
                        height: 40px;
                        border: 3px solid #e1e3e5;
                        border-top: 3px solid #008060;
                        border-radius: 50%;
                        animation: spin 1s linear infinite;
                        margin: 0 auto 16px;
                    "></div>
                    <div style="color: #6d7175; font-size: 14px;">${message}</div>
                </div>
                <style>
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                </style>
            </div>
        `;
        document.body.appendChild(overlay);
    }
    
    // Hide loading overlay
    hideLoading() {
        const overlay = document.getElementById('app-bridge-loading');
        if (overlay) {
            overlay.remove();
        }
    }
    
    // Build URL with proper parameters
    buildUrl(path, options = {}) {
        const urlParams = new URLSearchParams(window.location.search);
        const shop = urlParams.get('shop');
        const host = urlParams.get('host');
        
        let url = path;
        
        // Add query parameters
        const params = new URLSearchParams();
        
        if (shop) params.set('shop', shop);
        if (host) params.set('host', host);
        
        // Add custom parameters
        if (options.params) {
            Object.keys(options.params).forEach(key => {
                params.set(key, options.params[key]);
            });
        }
        
        const paramString = params.toString();
        if (paramString) {
            url += (url.includes('?') ? '&' : '?') + paramString;
        }
        
        return url;
    }
    
    // Get current shop
    getCurrentShop() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('shop');
    }
    
    // Get current host
    getCurrentHost() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('host');
    }
    
    // Check if embedded
    isEmbeddedApp() {
        return this.isEmbedded;
    }
    
    // Navigate back
    goBack() {
        if (this.isEmbedded && this.app) {
            window.history.back();
        } else {
            window.history.back();
        }
    }
    
    // Navigate to external URL
    navigateExternal(url) {
        if (this.isEmbedded && this.app) {
            this.app.dispatch(window.shopify.Action.OPEN, {
                url: url
            });
        } else {
            window.open(url, '_blank');
        }
    }
    
    // Refresh current page
    refresh() {
        if (this.isEmbedded && this.app) {
            this.app.dispatch(window.shopify.Action.RELOAD);
        } else {
            window.location.reload();
        }
    }
    
    // Close modal/dialog
    close() {
        if (this.isEmbedded && this.app) {
            this.app.dispatch(window.shopify.Action.CLOSE);
        }
    }
}

// Initialize navigation manager
const navigation = new AppBridgeNavigation();

// Helper functions for common navigation tasks
function navigateTo(path, options = {}) {
    navigation.navigate(path, options);
}

function navigateWithLoading(path, message) {
    navigation.navigateWithLoading(path, message);
}

function showToast(message, options = {}) {
    navigation.showToast(message, options);
}

function showModal(title, content, options = {}) {
    navigation.showModal(title, content, options);
}

function openExternal(url) {
    navigation.navigateExternal(url);
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('App Bridge Navigation ready');
});

// Make navigation available globally
window.AppBridgeNavigation = navigation;
window.navigateTo = navigateTo;
window.showToast = showToast;
window.showModal = showModal;
</script>
"""

def get_navigation_menu_items():
    """
    Get navigation menu items for the app
    """
    return [
        {
            "id": "dashboard",
            "label": "Dashboard",
            "icon": "📊",
            "path": "/dashboard",
            "description": "Overview and analytics"
        },
        {
            "id": "inventory",
            "label": "Inventory",
            "icon": "📦",
            "path": "/inventory",
            "description": "Manage inventory levels"
        },
        {
            "id": "orders",
            "label": "Orders",
            "icon": "🛒",
            "path": "/orders",
            "description": "Track and process orders"
        },
        {
            "id": "analytics",
            "label": "Analytics",
            "icon": "📈",
            "path": "/analytics",
            "description": "Detailed reports and insights"
        },
        {
            "id": "settings",
            "label": "Settings",
            "icon": "⚙️",
            "path": "/settings",
            "description": "App configuration"
        }
    ]

def create_navigation_sidebar(active_item=None):
    """
    Create navigation sidebar for embedded app
    """
    menu_items = get_navigation_menu_items()
    
    sidebar_html = """
    <div class="app-navigation" style="
        width: 240px;
        height: 100vh;
        background: #ffffff;
        border-right: 1px solid #e1e3e5;
        position: fixed;
        left: 0;
        top: 0;
        overflow-y: auto;
        z-index: 1000;
    ">
        <div class="nav-header" style="
            padding: 20px;
            border-bottom: 1px solid #e1e3e5;
        ">
            <div style="
                font-size: 16px;
                font-weight: 600;
                color: #202223;
                display: flex;
                align-items: center;
                gap: 8px;
            ">
                <span>🏢</span>
                <span>Employee Suite</span>
            </div>
        </div>
        
        <nav class="nav-menu" style="padding: 12px 0;">
    """
    
    for item in menu_items:
        is_active = active_item == item["id"]
        active_class = "nav-item-active" if is_active else ""
        
        sidebar_html += f"""
        <a href="#" onclick="navigateTo('{item['path']}'); return false;" class="nav-item {active_class}" style="
            display: flex;
            align-items: center;
            padding: 12px 20px;
            color: {'#202223;' if is_active else '#6d7175;'};
            text-decoration: none;
            font-size: 14px;
            font-weight: {'600;' if is_active else '400;'};
            background: {'#f6f6f7;' if is_active else 'transparent;'}
            border-left: 3px solid {'#008060;' if is_active else 'transparent;'}
            transition: all 0.15s ease;
        " onmouseover="this.style.background='{ '#f6f6f7;' if not is_active else 'transparent' }'" onmouseout="this.style.background='{ '#f6f6f7;' if is_active else 'transparent' }'">
            <span style="margin-right: 12px; font-size: 16px;">{item['icon']}</span>
            <span>{item['label']}</span>
        </a>
        """
    
    sidebar_html += """
        </nav>
        
        <div class="nav-footer" style="
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 20px;
            border-top: 1px solid #e1e3e5;
        ">
            <a href="/subscribe" onclick="navigateTo('/subscribe'); return false;" class="nav-upgrade-btn" style="
                display: block;
                background: #008060;
                color: white;
                text-align: center;
                padding: 12px;
                border-radius: 6px;
                text-decoration: none;
                font-size: 14px;
                font-weight: 500;
                transition: background 0.15s;
            " onmouseover="this.style.background='#006e52'" onmouseout="this.style.background='#008060'">
                ⭐ Upgrade Plan
            </a>
        </div>
    </div>
    
    <style>
        .nav-item:hover {
            background: #f6f6f7 !important;
            color: #202223 !important;
        }
        
        /* Main content margin for sidebar */
        .main-content {
            margin-left: 240px;
            min-height: 100vh;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .app-navigation {
                transform: translateX(-100%);
                transition: transform 0.3s ease;
            }
            
            .app-navigation.open {
                transform: translateX(0);
            }
            
            .main-content {
                margin-left: 0;
            }
        }
    </style>
    """
    
    return sidebar_html

def create_mobile_menu_toggle():
    """
    Create mobile menu toggle button
    """
    return """
    <button class="mobile-menu-toggle" onclick="toggleMobileMenu()" style="
        display: none;
        position: fixed;
        top: 20px;
        left: 20px;
        z-index: 1001;
        background: #008060;
        color: white;
        border: none;
        width: 40px;
        height: 40px;
        border-radius: 6px;
        font-size: 18px;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    ">
        ☰
    </button>
    
    <script>
        function toggleMobileMenu() {
            const nav = document.querySelector('.app-navigation');
            if (nav) {
                nav.classList.toggle('open');
            }
        }
        
        // Show mobile menu toggle on small screens
        function checkMobileMenu() {
            const toggle = document.querySelector('.mobile-menu-toggle');
            const nav = document.querySelector('.app-navigation');
            
            if (window.innerWidth <= 768) {
                if (toggle) toggle.style.display = 'block';
                if (nav) nav.classList.remove('open');
            } else {
                if (toggle) toggle.style.display = 'none';
                if (nav) nav.classList.add('open');
            }
        }
        
        window.addEventListener('resize', checkMobileMenu);
        document.addEventListener('DOMContentLoaded', checkMobileMenu);
    </script>
    """
