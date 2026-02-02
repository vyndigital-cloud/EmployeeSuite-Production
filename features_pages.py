"""
Frontend pages for enhanced features
- CSV exports page
- Scheduled reports page
- Comprehensive dashboard page
- Welcome/features page
"""
from flask import Blueprint, render_template, request, current_app
from flask_login import login_required, current_user
from access_control import require_access
from models import ShopifyStore
from app_bridge_integration import get_app_bridge_script

features_pages_bp = Blueprint('features', __name__)

# Welcome/Features Page
WELCOME_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Welcome to Employee Suite - New Features</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f6f6f7;
            color: #202223;
            line-height: 1.6;
        }
        .header {
            background: #ffffff;
            border-bottom: 1px solid #e1e3e5;
            padding: 20px 0;
        }
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        .hero {
            text-align: center;
            padding: 60px 20px;
            background: linear-gradient(135deg, #008060 0%, #006e52 100%);
            color: white;
            border-radius: 16px;
            margin-bottom: 60px;
        }
        .hero h1 {
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 16px;
        }
        .hero p {
            font-size: 20px;
            opacity: 0.95;
            margin-bottom: 32px;
        }
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
            margin-bottom: 60px;
        }
        .feature-card {
            background: #ffffff;
            border: 1px solid #e1e3e5;
            border-radius: 12px;
            padding: 32px;
            transition: all 0.3s ease;
        }
        .feature-card:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            transform: translateY(-2px);
        }
        .feature-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }
        .feature-title {
            font-size: 24px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 12px;
        }
        .feature-description {
            font-size: 15px;
            color: #6d7175;
            margin-bottom: 20px;
            line-height: 1.6;
        }
        .feature-link {
            display: inline-block;
            padding: 10px 20px;
            background: #008060;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            transition: background 0.2s;
        }
        .feature-link:hover {
            background: #006e52;
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            background: #f0fdf4;
            color: #166534;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 8px;
        }
    </style>
    <script>
        // CRITICAL: Robust navigation helper to preserve embedded context
        window.openPage = function(path) {
            var params = new URLSearchParams(window.location.search);
            var shop = params.get('shop');
            var host = params.get('host');
            var embedded = params.get('embedded') || (host ? '1' : '');
            
            var sep = path.indexOf('?') > -1 ? '&' : '?';
            var dest = path;
            
            if (shop) dest += sep + 'shop=' + shop;
            if (host) dest += (dest.indexOf('?') > -1 ? '&' : '?') + 'host=' + host;
            if (embedded) dest += (dest.indexOf('?') > -1 ? '&' : '?') + 'embedded=' + embedded;
            
            window.location.href = dest;
            return false;
        };
    </script>
</head>
<body>
        <div class="header">
            <div class="header-content">
                <a href="#" onclick="openPage('/dashboard'); return false;" style="text-decoration: none; color: inherit; font-weight: 600; font-size: 18px;">← Employee Suite</a>
            <div style="display: flex; gap: 12px; align-items: center;">
                <a href="#" onclick="openPage('/dashboard'); return false;" style="color: #6d7175; text-decoration: none; padding: 6px 12px; border-radius: 6px; transition: background 0.15s;">Dashboard</a>
                <a href="#" onclick="openPage('/features/csv-exports'); return false;" style="color: #6d7175; text-decoration: none; padding: 6px 12px; border-radius: 6px; transition: background 0.15s;">CSV Exports</a>
                <a href="#" onclick="openPage('/features/scheduled-reports'); return false;" style="color: #6d7175; text-decoration: none; padding: 6px 12px; border-radius: 6px; transition: background 0.15s;">Scheduled</a>
                <a href="#" onclick="openPage('/features/dashboard'); return false;" style="color: #6d7175; text-decoration: none; padding: 6px 12px; border-radius: 6px; transition: background 0.15s;">Full Dashboard</a>
                <a href="#" onclick="openPage('/subscribe'); return false;" style="color: #008060; text-decoration: none; font-weight: 500; padding: 6px 12px;">Subscribe</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="hero">
            <h1>🎉 Welcome to Employee Suite Premium</h1>
            <p>Discover powerful new features designed to save you time and grow your business</p>
            <div style="font-size: 16px; opacity: 0.9;">
                <strong>$99/month</strong> • 7-day free trial • Cancel anytime
            </div>
        </div>
        
        <div class="features-grid">
            <div class="feature-card">
                <div class="feature-icon">📥</div>
                <div class="feature-title">CSV Exports <span class="badge">NEW</span></div>
                <div class="feature-description">
                    Download Orders, Inventory, and Revenue reports as CSV files. Filter by date ranges, export anytime, and analyze your data in Excel or Google Sheets.
                </div>
                <a href="/features/csv-exports{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" class="feature-link">Export Data →</a>
            </div>
            
            <div class="feature-card">
                <div class="feature-icon">📅</div>
                <div class="feature-title">Scheduled Reports <span class="badge">NEW</span></div>
                <div class="feature-description">
                    Automatically receive reports via Email or SMS at your preferred time. Set daily, weekly, or monthly schedules. Never miss important updates.
                </div>
                <a href="/features/scheduled-reports{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" class="feature-link">Schedule Reports →</a>
            </div>
            
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <div class="feature-title">Comprehensive Dashboard <span class="badge">NEW</span></div>
                <div class="feature-description">
                    View all three reports (Orders, Inventory, Revenue) in one unified dashboard. Get a complete overview of your store's performance at a glance.
                </div>
                <a href="/features/dashboard{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" class="feature-link">View Dashboard →</a>
            </div>
            
            <div class="feature-card">
                <div class="feature-icon">🔒</div>
                <div class="feature-title">Data Encryption</div>
                <div class="feature-description">
                    Your sensitive data is encrypted at rest. Access tokens and personal information are protected with industry-standard encryption.
                </div>
                <div style="color: #008060; font-weight: 500; margin-top: 20px;">✓ Always Active</div>
            </div>
            
            <div class="feature-card">
                <div class="feature-icon">📦</div>
                <div class="feature-title">Order Processing</div>
                <div class="feature-description">
                    View pending and unfulfilled Shopify orders. Monitor order status, payment information, and customer details in real-time.
                </div>
                <a href="/dashboard{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" class="feature-link">View Orders →</a>
            </div>
            
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <div class="feature-title">Inventory Management</div>
                <div class="feature-description">
                    Monitor stock levels across all products. Get low-stock alerts and complete inventory visibility to prevent stockouts.
                </div>
                <a href="/dashboard{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" class="feature-link">Check Inventory →</a>
            </div>
            
            <div class="feature-card">
                <div class="feature-icon">💰</div>
                <div class="feature-title">Revenue Analytics</div>
                <div class="feature-description">
                    Generate detailed revenue reports with product-level breakdown and insights. Track your store's financial performance over time.
                </div>
                <a href="/dashboard{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" class="feature-link">Generate Report →</a>
            </div>
            
            <div class="feature-card">
                <div class="feature-icon">⚙️</div>
                <div class="feature-title">Auto-Download Settings</div>
                <div class="feature-description">
                    Configure automatic downloads for your reports. Set preferences for each report type and streamline your workflow.
                </div>
                <a href="/features/csv-exports{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" class="feature-link">Configure →</a>
            </div>
        </div>
        
        <div style="text-align: center; padding: 40px 20px; background: #ffffff; border-radius: 12px; border: 1px solid #e1e3e5;">
            <h2 style="font-size: 32px; font-weight: 600; margin-bottom: 16px;">Ready to Get Started?</h2>
            <p style="font-size: 16px; color: #6d7175; margin-bottom: 32px;">Start your 7-day free trial today. No credit card required.</p>
            <a href="/subscribe{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" style="display: inline-block; padding: 14px 32px; background: #008060; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px;">Start Free Trial →</a>
        </div>
    </div>
</body>
</html>
'''

@features_pages_bp.route('/features/welcome')
@login_required
def welcome():
    """Welcome page showcasing all new features"""
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    
    # Render new template
    return render_template('features/welcome.html', shop=shop, host=host)

@features_pages_bp.route('/features/csv-exports')
@login_required
@require_access
def csv_exports_page():
    """CSV exports page with date filtering"""
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    
    # Check if store is connected
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    has_store = store is not None
    
    return render_template('features/csv_exports.html', shop=shop, host=host, has_store=has_store)

@features_pages_bp.route('/features/scheduled-reports')
@login_required
@require_access
def scheduled_reports_page():
    """Scheduled reports management page with full UI"""
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    
    return render_template('features/scheduled_reports.html', shop=shop, host=host)

@features_pages_bp.route('/features/dashboard')
@login_required
@require_access
def comprehensive_dashboard_page():
    """Comprehensive dashboard page showing all reports"""
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    
    return render_template('features/dashboard.html', shop=shop, host=host)

