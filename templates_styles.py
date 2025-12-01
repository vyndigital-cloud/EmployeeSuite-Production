# Shared HTML template styles for consistent design across all pages

BASE_STYLES = """
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: #fafafa;
        color: #171717;
        -webkit-font-smoothing: antialiased;
        min-height: 100vh;
    }
    
    /* Header */
    .header {
        background: #fff;
        border-bottom: 1px solid #e5e5e5;
    }
    .header-content {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 24px;
        height: 64px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .logo {
        font-size: 18px;
        font-weight: 600;
        color: #171717;
        text-decoration: none;
    }
    .header-nav {
        display: flex;
        gap: 8px;
        align-items: center;
    }
    .nav-btn {
        padding: 8px 14px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 500;
        text-decoration: none;
        border: none;
        cursor: pointer;
        transition: background 0.2s;
        background: transparent;
        color: #525252;
    }
    .nav-btn:hover {
        background: #f5f5f5;
    }
    
    /* Container */
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 48px 24px;
    }
    .container-narrow {
        max-width: 480px;
        margin: 0 auto;
        padding: 48px 24px;
    }
    
    /* Page Header */
    .page-header {
        margin-bottom: 32px;
    }
    .page-title {
        font-size: 32px;
        font-weight: 700;
        color: #171717;
        margin-bottom: 8px;
    }
    .page-subtitle {
        font-size: 16px;
        color: #737373;
    }
    
    /* Card */
    .card {
        background: #fff;
        border: 1px solid #e5e5e5;
        border-radius: 12px;
        padding: 32px;
    }
    .card-header {
        margin-bottom: 24px;
    }
    .card-title {
        font-size: 20px;
        font-weight: 600;
        color: #171717;
        margin-bottom: 4px;
    }
    .card-subtitle {
        font-size: 14px;
        color: #737373;
    }
    
    /* Forms */
    .form-group {
        margin-bottom: 20px;
    }
    .form-label {
        display: block;
        font-size: 14px;
        font-weight: 500;
        color: #171717;
        margin-bottom: 8px;
    }
    .form-input {
        width: 100%;
        padding: 12px;
        border: 1px solid #e5e5e5;
        border-radius: 6px;
        font-size: 14px;
        font-family: inherit;
        transition: border-color 0.2s;
    }
    .form-input:focus {
        outline: none;
        border-color: #171717;
    }
    .form-help {
        font-size: 13px;
        color: #737373;
        margin-top: 6px;
    }
    
    /* Buttons */
    .btn {
        padding: 12px 20px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 500;
        border: none;
        cursor: pointer;
        transition: all 0.2s;
        text-decoration: none;
        display: inline-block;
        text-align: center;
    }
    .btn-primary {
        background: #171717;
        color: #fff;
    }
    .btn-primary:hover {
        background: #262626;
    }
    .btn-secondary {
        background: #f5f5f5;
        color: #171717;
    }
    .btn-secondary:hover {
        background: #e5e5e5;
    }
    .btn-full {
        width: 100%;
    }
    
    /* Banner */
    .banner {
        background: #fff;
        border: 1px solid #e5e5e5;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
    }
    .banner-success {
        border-left: 3px solid #16a34a;
        background: #f0fdf4;
    }
    .banner-error {
        border-left: 3px solid #dc2626;
        background: #fef2f2;
    }
    .banner-warning {
        border-left: 3px solid #f59e0b;
        background: #fffbeb;
    }
    .banner-info {
        border-left: 3px solid #3b82f6;
        background: #eff6ff;
    }
    
    /* Lists */
    .info-list {
        list-style: none;
        margin: 24px 0;
    }
    .info-list li {
        padding: 12px 0;
        border-bottom: 1px solid #f5f5f5;
        display: flex;
        justify-content: space-between;
        font-size: 14px;
    }
    .info-list li:last-child {
        border-bottom: none;
    }
    .info-label {
        color: #737373;
        font-weight: 500;
    }
    .info-value {
        color: #171717;
        font-weight: 500;
    }
    
    /* Table */
    .table-container {
        overflow-x: auto;
        margin-top: 24px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
    }
    th {
        text-align: left;
        padding: 12px;
        font-size: 13px;
        font-weight: 600;
        color: #737373;
        border-bottom: 1px solid #e5e5e5;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    td {
        padding: 16px 12px;
        font-size: 14px;
        color: #171717;
        border-bottom: 1px solid #f5f5f5;
    }
    
    /* Badge */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-success {
        background: #dcfce7;
        color: #166534;
    }
    .badge-warning {
        background: #fef3c7;
        color: #92400e;
    }
    .badge-error {
        background: #fee2e2;
        color: #991b1b;
    }
    
    /* Links */
    a {
        color: #171717;
        text-decoration: underline;
    }
    a:hover {
        color: #525252;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .container { padding: 32px 16px; }
        .container-narrow { padding: 32px 16px; }
        .page-title { font-size: 24px; }
        .card { padding: 24px; }
    }
</style>
"""

def get_header(current_page='dashboard', show_nav=True):
    """Generate consistent header for all pages"""
    nav_html = ''
    if show_nav:
        nav_html = '''
        <div class="header-nav">
            <a href="/dashboard" class="nav-btn">Dashboard</a>
            <a href="/settings/shopify" class="nav-btn">Settings</a>
            <a href="/subscribe" class="nav-btn">Subscribe</a>
            <a href="/logout" class="nav-btn">Logout</a>
        </div>
        '''
    
    return f'''
    <div class="header">
        <div class="header-content">
            <a href="/dashboard" class="logo">Employee Suite</a>
            {nav_html}
        </div>
    </div>
    '''
