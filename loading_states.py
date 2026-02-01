"""
Loading States and Progress Indicators - Shopify Best Practices
Implements proper loading states for embedded Shopify apps
"""

def create_polaris_loading_overlay(message="Loading...", size="large"):
    """
    Create Polaris-style loading overlay
    """
    size_class = "Polaris-Spinner--sizeLarge" if size == "large" else "Polaris-Spinner--sizeSmall"
    
    return f"""
    <div id="loading-overlay" class="loading-overlay" style="
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.95);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    ">
        <div class="loading-content" style="text-align: center;">
            <div class="Polaris-Spinner {size_class}" style="
                width: {48 if size == 'large' else 24}px;
                height: {48 if size == 'large' else 24}px;
                border: 3px solid #e1e3e5;
                border-top: 3px solid #008060;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 16px;
            "></div>
            <div class="loading-message" style="
                color: #6d7175;
                font-size: 14px;
                font-weight: 400;
                margin-top: 12px;
            ">{message}</div>
        </div>
        <style>
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </div>
    """

def create_progress_bar(progress=0, message="Processing...", show_percentage=True):
    """
    Create progress bar with percentage
    """
    return f"""
    <div class="progress-container" style="
        background: white;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        max-width: 400px;
        margin: 20px auto;
    ">
        <div class="progress-message" style="
            font-size: 14px;
            color: #202223;
            margin-bottom: 12px;
            font-weight: 500;
        ">{message}</div>
        <div class="progress-bar-wrapper" style="
            background: #f6f6f7;
            border-radius: 4px;
            height: 8px;
            overflow: hidden;
            margin-bottom: 8px;
        ">
            <div class="progress-bar-fill" style="
                background: #008060;
                height: 100%;
                width: {progress}%;
                transition: width 0.3s ease;
                border-radius: 4px;
            "></div>
        </div>
        {f'<div class="progress-percentage" style="font-size: 12px; color: #6d7175; text-align: right;">{progress}%</div>' if show_percentage else ''}
    </div>
    """

def create_skeleton_loader(items=3):
    """
    Create skeleton loader for content
    """
    skeleton_items = ""
    for i in range(items):
        skeleton_items += f"""
        <div class="skeleton-item" style="
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        ">
            <div class="skeleton-header" style="
                display: flex;
                align-items: center;
                margin-bottom: 16px;
            ">
                <div class="skeleton-avatar" style="
                    width: 40px;
                    height: 40px;
                    background: #f6f6f7;
                    border-radius: 50%;
                    margin-right: 12px;
                "></div>
                <div class="skeleton-title" style="
                    width: 120px;
                    height: 16px;
                    background: #f6f6f7;
                    border-radius: 4px;
                "></div>
            </div>
            <div class="skeleton-content" style="
                width: 100%;
                height: 12px;
                background: #f6f6f7;
                border-radius: 4px;
                margin-bottom: 8px;
            "></div>
            <div class="skeleton-content" style="
                width: 80%;
                height: 12px;
                background: #f6f6f7;
                border-radius: 4px;
            "></div>
        </div>
        """
    
    return f"""
    <div class="skeleton-loader">
        {skeleton_items}
        <style>
            @keyframes shimmer {{
                0% {{ background-position: -1000px 0; }}
                100% {{ background-position: 1000px 0; }}
            }}
            .skeleton-item > div {{
                animation: shimmer 2s infinite linear;
                background: linear-gradient(90deg, #f6f6f7 25%, #e1e3e5 50%, #f6f6f7 75%);
                background-size: 1000px 100%;
            }}
        </style>
    </div>
    """

def create_step_indicator(current_step=1, total_steps=4, steps=None):
    """
    Create step indicator for multi-step processes
    """
    if not steps:
        steps = ["Step 1", "Step 2", "Step 3", "Step 4"]
    
    step_html = ""
    for i in range(total_steps):
        step_number = i + 1
        is_completed = step_number < current_step
        is_current = step_number == current_step
        is_upcoming = step_number > current_step
        
        status_class = "completed" if is_completed else "current" if is_current else "upcoming"
        
        step_html += f"""
        <div class="step-item {status_class}" style="
            display: flex;
            align-items: center;
            flex: 1;
        ">
            <div class="step-circle" style="
                width: 32px;
                height: 32px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
                font-weight: 600;
                {'background: #008060; color: white;' if is_completed else 'background: #008060; color: white;' if is_current else 'background: #f6f6f7; color: #6d7175;'}
            ">
                {'✓' if is_completed else step_number}
            </div>
            <div class="step-label" style="
                margin-left: 8px;
                font-size: 12px;
                color: {'#202223;' if is_current else '#6d7175;'}
                font-weight: {'600;' if is_current else '400;'}
            ">{steps[i] if i < len(steps) else f'Step {step_number}'}</div>
        </div>
        """
        
        if i < total_steps - 1:
            step_html += f"""
            <div class="step-connector" style="
                width: 40px;
                height: 2px;
                background: {'#008060;' if is_completed else '#e1e3e5;'}
                margin: 0 8px;
            "></div>
            """
    
    return f"""
    <div class="step-indicator" style="
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
        background: white;
        border-radius: 8px;
        margin-bottom: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    ">
        {step_html}
    </div>
    """

def create_empty_state(title, message, action_text=None, action_url=None):
    """
    Create empty state placeholder
    """
    action_html = ""
    if action_text and action_url:
        action_html = f"""
        <button class="empty-state-action" onclick="window.location.href='{action_url}'" style="
            background: #008060;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            margin-top: 16px;
            transition: background 0.15s;
        " onmouseover="this.style.background='#006e52'" onmouseout="this.style.background='#008060'">
            {action_text}
        </button>
        """
    
    return f"""
    <div class="empty-state" style="
        text-align: center;
        padding: 60px 20px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    ">
        <div class="empty-state-icon" style="
            font-size: 48px;
            margin-bottom: 16px;
            opacity: 0.5;
        ">📦</div>
        <div class="empty-state-title" style="
            font-size: 18px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 8px;
        ">{title}</div>
        <div class="empty-state-message" style="
            font-size: 14px;
            color: #6d7175;
            line-height: 1.5;
            max-width: 400px;
            margin: 0 auto;
        ">{message}</div>
        {action_html}
    </div>
    """

# JavaScript functions for loading states
LOADING_JS = """
<script>
// Loading state management
const LoadingManager = {
    show: function(message, size) {
        this.hide();
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.innerHTML = `""" + create_polaris_loading_overlay("${message}", "${size}") + """`;
        document.body.appendChild(overlay);
    },
    
    hide: function() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    },
    
    showProgress: function(progress, message) {
        let container = document.getElementById('progress-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'progress-container';
            container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
            document.body.appendChild(container);
        }
        container.innerHTML = `""" + create_progress_bar("${progress}", "${message}") + """`.replace('${progress}', progress).replace('${message}', message);
    },
    
    hideProgress: function() {
        const container = document.getElementById('progress-container');
        if (container) {
            container.remove();
        }
    },
    
    showSkeleton: function(containerId, items) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `""" + create_skeleton_loader("${items}") + """`.replace('${items}', items || 3);
        }
    },
    
    showStepIndicator: function(currentStep, totalSteps, steps) {
        let container = document.getElementById('step-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'step-container';
            document.body.insertBefore(container, document.body.firstChild);
        }
        container.innerHTML = `""" + create_step_indicator("${currentStep}", "${totalSteps}", "${steps}") + """`;
    }
};

// Auto-hide loading after 30 seconds (safety net)
setTimeout(function() {
    LoadingManager.hide();
}, 30000);
</script>
"""

def get_loading_html():
    """
    Get complete loading HTML with CSS and JavaScript
    """
    return f"""
    <style>
        .loading-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.95);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        
        .Polaris-Spinner {{
            border: 3px solid #e1e3e5;
            border-top: 3px solid #008060;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}
        
        .Polaris-Spinner--sizeLarge {{
            width: 48px;
            height: 48px;
        }}
        
        .Polaris-Spinner--sizeSmall {{
            width: 24px;
            height: 24px;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .fade-in {{
            animation: fadeIn 0.3s ease-in;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
    </style>
    
    {LOADING_JS}
    """
