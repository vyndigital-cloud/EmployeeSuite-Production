"""
Frontend pages for enhanced features
- CSV exports page
- Scheduled reports page
- Comprehensive dashboard page
- Welcome/features page
"""
from flask import Blueprint, render_template_string, request, current_app
from flask_login import login_required, current_user
from access_control import require_access
from models import ShopifyStore

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
</head>
<body>
    <div class="header">
        <div class="header-content">
            <a href="/dashboard{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" style="text-decoration: none; color: inherit; font-weight: 600; font-size: 18px;">Employee Suite</a>
            <div>
                <a href="/dashboard{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" style="color: #6d7175; text-decoration: none; margin-right: 20px;">Dashboard</a>
                <a href="/subscribe{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" style="color: #008060; text-decoration: none; font-weight: 500;">Subscribe</a>
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
    return render_template_string(WELCOME_HTML, shop=shop, host=host)

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
    
    HTML = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>CSV Exports - Employee Suite</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f6f6f7;
                color: #202223;
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
                max-width: 1000px;
                margin: 0 auto;
                padding: 40px 20px;
            }
            .card {
                background: #ffffff;
                border: 1px solid #e1e3e5;
                border-radius: 12px;
                padding: 32px;
                margin-bottom: 24px;
            }
            .card-title {
                font-size: 24px;
                font-weight: 600;
                margin-bottom: 16px;
            }
            .date-filter {
                display: flex;
                gap: 12px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }
            .date-input {
                padding: 10px 14px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 14px;
            }
            .btn {
                padding: 10px 20px;
                background: #008060;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 500;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
            }
            .btn:hover {
                background: #006e52;
            }
            .btn-secondary {
                background: #6d7175;
            }
            .btn-secondary:hover {
                background: #525252;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <a href="/dashboard{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" style="text-decoration: none; color: inherit; font-weight: 600; font-size: 18px;">← Back to Dashboard</a>
            </div>
        </div>
        
        <div class="container">
            <h1 style="font-size: 32px; font-weight: 600; margin-bottom: 8px;">CSV Exports</h1>
            <p style="color: #6d7175; margin-bottom: 32px;">Download your data as CSV files with date filtering</p>
            
            {% if not has_store %}
            <div class="card" style="background: #fff4f4; border-color: #fecaca;">
                <p style="color: #d72c0d; font-weight: 600;">⚠️ Connect your Shopify store first</p>
                <a href="/settings/shopify{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" class="btn">Connect Store →</a>
            </div>
            {% else %}
            
            <div class="card">
                <div class="card-title">📦 Export Orders</div>
                <div class="date-filter">
                    <input type="date" id="orders-start" class="date-input" placeholder="Start Date">
                    <input type="date" id="orders-end" class="date-input" placeholder="End Date">
                    <a href="#" id="export-orders" class="btn">Export Orders CSV</a>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">📊 Export Inventory</div>
                <div class="date-filter">
                    <input type="number" id="inventory-days" class="date-input" placeholder="Days (e.g., 30)" value="30" style="width: 150px;">
                    <a href="#" id="export-inventory" class="btn">Export Inventory CSV</a>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">💰 Export Revenue</div>
                <div class="date-filter">
                    <input type="date" id="revenue-start" class="date-input" placeholder="Start Date">
                    <input type="date" id="revenue-end" class="date-input" placeholder="End Date">
                    <a href="#" id="export-revenue" class="btn">Export Revenue CSV</a>
                </div>
            </div>
            
            {% endif %}
        </div>
        
        <script>
            // Show success message
            function showSuccess(message) {
                const alert = document.createElement('div');
                alert.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #f0fdf4; border: 1px solid #86efac; color: #166534; padding: 12px 20px; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000;';
                alert.textContent = message;
                document.body.appendChild(alert);
                setTimeout(() => alert.remove(), 3000);
            }
            
            // Export handlers with loading states
            document.getElementById('export-orders')?.addEventListener('click', function(e) {
                e.preventDefault();
                const btn = this;
                const originalText = btn.textContent;
                btn.textContent = 'Exporting...';
                btn.style.opacity = '0.6';
                btn.style.pointerEvents = 'none';
                
                const start = document.getElementById('orders-start').value;
                const end = document.getElementById('orders-end').value;
                let url = '/api/export/orders';
                if (start) url += '?start_date=' + start;
                if (end) url += (start ? '&' : '?') + 'end_date=' + end;
                
                // Trigger download
                const link = document.createElement('a');
                link.href = url;
                link.download = '';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.style.opacity = '1';
                    btn.style.pointerEvents = 'auto';
                    showSuccess('Orders CSV export started');
                }, 500);
            });
            
            document.getElementById('export-inventory')?.addEventListener('click', function(e) {
                e.preventDefault();
                const btn = this;
                const originalText = btn.textContent;
                btn.textContent = 'Exporting...';
                btn.style.opacity = '0.6';
                btn.style.pointerEvents = 'none';
                
                const days = document.getElementById('inventory-days').value;
                const url = '/api/export/inventory?days=' + (days || 30);
                
                const link = document.createElement('a');
                link.href = url;
                link.download = '';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.style.opacity = '1';
                    btn.style.pointerEvents = 'auto';
                    showSuccess('Inventory CSV export started');
                }, 500);
            });
            
            document.getElementById('export-revenue')?.addEventListener('click', function(e) {
                e.preventDefault();
                const btn = this;
                const originalText = btn.textContent;
                btn.textContent = 'Exporting...';
                btn.style.opacity = '0.6';
                btn.style.pointerEvents = 'none';
                
                const start = document.getElementById('revenue-start').value;
                const end = document.getElementById('revenue-end').value;
                let url = '/api/export/revenue';
                if (start) url += '?start_date=' + start;
                if (end) url += (start ? '&' : '?') + 'end_date=' + end;
                
                const link = document.createElement('a');
                link.href = url;
                link.download = '';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.style.opacity = '1';
                    btn.style.pointerEvents = 'auto';
                    showSuccess('Revenue CSV export started');
                }, 500);
            });
        </script>
    </body>
    </html>
    '''
    return render_template_string(HTML, shop=shop, host=host, has_store=has_store)

@features_pages_bp.route('/features/scheduled-reports')
@login_required
@require_access
def scheduled_reports_page():
    """Scheduled reports management page with full UI"""
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    
    HTML = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Scheduled Reports - Employee Suite</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f6f6f7;
                color: #202223;
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
            }
            .container {
                max-width: 1000px;
                margin: 0 auto;
                padding: 40px 20px;
            }
            .card {
                background: #ffffff;
                border: 1px solid #e1e3e5;
                border-radius: 12px;
                padding: 32px;
                margin-bottom: 24px;
            }
            .card-title {
                font-size: 24px;
                font-weight: 600;
                margin-bottom: 16px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-label {
                display: block;
                font-weight: 500;
                margin-bottom: 8px;
                color: #202223;
            }
            .form-input, .form-select {
                width: 100%;
                padding: 10px 14px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 14px;
                font-family: inherit;
            }
            .form-input:focus, .form-select:focus {
                outline: none;
                border-color: #008060;
                box-shadow: 0 0 0 3px rgba(0, 128, 96, 0.1);
            }
            .btn {
                padding: 10px 20px;
                background: #008060;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 500;
                cursor: pointer;
                font-size: 14px;
                transition: background 0.2s;
            }
            .btn:hover {
                background: #006e52;
            }
            .btn-danger {
                background: #d72c0d;
            }
            .btn-danger:hover {
                background: #b01e1e;
            }
            .btn-secondary {
                background: #6d7175;
            }
            .btn-secondary:hover {
                background: #525252;
            }
            .reports-list {
                margin-top: 32px;
            }
            .report-item {
                background: #f6f6f7;
                border: 1px solid #e1e3e5;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 12px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .report-info h3 {
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 8px;
            }
            .report-info p {
                font-size: 14px;
                color: #6d7175;
                margin: 4px 0;
            }
            .alert {
                padding: 12px 16px;
                border-radius: 6px;
                margin-bottom: 20px;
            }
            .alert-success {
                background: #f0fdf4;
                border: 1px solid #86efac;
                color: #166534;
            }
            .alert-error {
                background: #fff4f4;
                border: 1px solid #fecaca;
                color: #d72c0d;
            }
            .alert-info {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                color: #1e40af;
            }
            .loading {
                opacity: 0.6;
                pointer-events: none;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <a href="/dashboard{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" style="text-decoration: none; color: inherit; font-weight: 600; font-size: 18px;">← Back to Dashboard</a>
            </div>
        </div>
        
        <div class="container">
            <h1 style="font-size: 32px; font-weight: 600; margin-bottom: 8px;">Scheduled Reports</h1>
            <p style="color: #6d7175; margin-bottom: 32px;">Automatically receive reports via Email or SMS at your preferred time</p>
            
            <div id="alert-container"></div>
            
            <div class="card">
                <div class="card-title">Create New Scheduled Report</div>
                <form id="create-report-form">
                    <div class="form-group">
                        <label class="form-label">Report Type</label>
                        <select name="report_type" class="form-select" required>
                            <option value="all">All Reports (Orders, Inventory, Revenue)</option>
                            <option value="orders">Orders Only</option>
                            <option value="inventory">Inventory Only</option>
                            <option value="revenue">Revenue Only</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Frequency</label>
                        <select name="frequency" class="form-select" required>
                            <option value="daily">Daily</option>
                            <option value="weekly">Weekly</option>
                            <option value="monthly">Monthly</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Delivery Time</label>
                        <input type="time" name="delivery_time" class="form-input" value="09:00" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Delivery Email</label>
                        <input type="email" name="delivery_email" class="form-input" placeholder="your@email.com" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Delivery SMS (Optional)</label>
                        <input type="tel" name="delivery_sms" class="form-input" placeholder="+1234567890">
                        <small style="color: #6d7175; font-size: 12px; display: block; margin-top: 4px;">Phone number in E.164 format (e.g., +1234567890)</small>
                    </div>
                    
                    <button type="submit" class="btn" id="create-btn">Create Scheduled Report</button>
                </form>
            </div>
            
            <div class="reports-list">
                <div class="card-title">Active Scheduled Reports</div>
                <div id="reports-container">
                    <p style="color: #6d7175; text-align: center; padding: 40px;">Loading reports...</p>
                </div>
            </div>
        </div>
        
        <script>
            // Show alert function
            function showAlert(message, type) {
                const container = document.getElementById('alert-container');
                const alert = document.createElement('div');
                alert.className = `alert alert-${type}`;
                alert.textContent = message;
                container.innerHTML = '';
                container.appendChild(alert);
                setTimeout(() => alert.remove(), 5000);
            }
            
            // Load reports
            async function loadReports() {
                try {
                    const response = await fetch('/api/scheduled-reports');
                    const data = await response.json();
                    
                    const container = document.getElementById('reports-container');
                    
                    if (!data.reports || data.reports.length === 0) {
                        container.innerHTML = '<p style="color: #6d7175; text-align: center; padding: 40px;">No scheduled reports yet. Create one above to get started.</p>';
                        return;
                    }
                    
                    container.innerHTML = data.reports.map(report => `
                        <div class="report-item">
                            <div class="report-info">
                                <h3>${report.report_type.charAt(0).toUpperCase() + report.report_type.slice(1)} Report</h3>
                                <p><strong>Frequency:</strong> ${report.frequency.charAt(0).toUpperCase() + report.frequency.slice(1)}</p>
                                <p><strong>Time:</strong> ${report.delivery_time} ${report.timezone}</p>
                                <p><strong>Email:</strong> ${report.delivery_email || 'Not set'}</p>
                                ${report.delivery_sms ? `<p><strong>SMS:</strong> ${report.delivery_sms}</p>` : ''}
                                ${report.next_send_at ? `<p><strong>Next Send:</strong> ${new Date(report.next_send_at).toLocaleString()}</p>` : ''}
                            </div>
                            <button class="btn btn-danger" onclick="deleteReport(${report.id})">Delete</button>
                        </div>
                    `).join('');
                } catch (error) {
                    document.getElementById('reports-container').innerHTML = 
                        '<p style="color: #d72c0d; text-align: center; padding: 40px;">Error loading reports. Please refresh the page.</p>';
                }
            }
            
            // Delete report
            async function deleteReport(id) {
                if (!confirm('Are you sure you want to delete this scheduled report?')) return;
                
                try {
                    const response = await fetch(`/api/scheduled-reports/${id}`, {
                        method: 'DELETE'
                    });
                    const data = await response.json();
                    
                    if (data.success) {
                        showAlert('Scheduled report deleted successfully', 'success');
                        loadReports();
                    } else {
                        showAlert(data.error || 'Failed to delete report', 'error');
                    }
                } catch (error) {
                    showAlert('Error deleting report. Please try again.', 'error');
                }
            }
            
            // Create report form
            document.getElementById('create-report-form').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const form = e.target;
                const btn = document.getElementById('create-btn');
                const formData = new FormData(form);
                const data = Object.fromEntries(formData);
                
                btn.disabled = true;
                btn.textContent = 'Creating...';
                form.classList.add('loading');
                
                try {
                    const response = await fetch('/api/scheduled-reports', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showAlert('Scheduled report created successfully!', 'success');
                        form.reset();
                        loadReports();
                    } else {
                        showAlert(result.error || 'Failed to create scheduled report', 'error');
                    }
                } catch (error) {
                    showAlert('Error creating scheduled report. Please try again.', 'error');
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Create Scheduled Report';
                    form.classList.remove('loading');
                }
            });
            
            // Load reports on page load
            loadReports();
        </script>
    </body>
    </html>
    '''
    return render_template_string(HTML, shop=shop, host=host)

@features_pages_bp.route('/features/dashboard')
@login_required
@require_access
def comprehensive_dashboard_page():
    """Comprehensive dashboard page showing all reports"""
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    
    HTML = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Comprehensive Dashboard - Employee Suite</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f6f6f7;
                color: #202223;
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
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 20px;
            }
            .card {
                background: #ffffff;
                border: 1px solid #e1e3e5;
                border-radius: 12px;
                padding: 32px;
                margin-bottom: 24px;
            }
            .btn {
                padding: 10px 20px;
                background: #008060;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 500;
                cursor: pointer;
            }
            #dashboard-content {
                min-height: 400px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <a href="/dashboard{% if shop %}?shop={{ shop }}{% if host %}&host={{ host }}{% endif %}{% endif %}" style="text-decoration: none; color: inherit; font-weight: 600;">← Back to Dashboard</a>
            </div>
        </div>
        
        <div class="container">
            <h1 style="font-size: 32px; font-weight: 600; margin-bottom: 8px;">Comprehensive Dashboard</h1>
            <p style="color: #6d7175; margin-bottom: 32px;">View all reports in one place</p>
            
            <div class="card">
                <button class="btn" onclick="loadDashboard()" style="margin-bottom: 24px;">Load All Reports</button>
                <div id="dashboard-content">
                    <p style="color: #6d7175;">Click "Load All Reports" to fetch orders, inventory, and revenue data.</p>
                </div>
            </div>
        </div>
        
        <script>
            async function loadDashboard() {
                const content = document.getElementById('dashboard-content');
                content.innerHTML = '<p>Loading...</p>';
                
                try {
                    const response = await fetch('/api/dashboard/comprehensive');
                    const data = await response.json();
                    
                    if (data.success) {
                        content.innerHTML = `
                            <h2 style="margin-bottom: 16px;">Orders</h2>
                            <div style="margin-bottom: 32px;">${data.orders || 'No orders data'}</div>
                            
                            <h2 style="margin-bottom: 16px;">Inventory</h2>
                            <div style="margin-bottom: 32px;">${data.inventory || 'No inventory data'}</div>
                            
                            <h2 style="margin-bottom: 16px;">Revenue</h2>
                            <div>${data.revenue || 'No revenue data'}</div>
                        `;
                    } else {
                        content.innerHTML = '<p style="color: #d72c0d;">Error: ' + (data.error || 'Unknown error') + '</p>';
                    }
                } catch (error) {
                    content.innerHTML = '<p style="color: #d72c0d;">Error loading dashboard: ' + error.message + '</p>';
                }
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(HTML, shop=shop, host=host)

