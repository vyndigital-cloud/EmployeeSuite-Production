from flask import Blueprint, render_template_string, request

features_bp = Blueprint("features", __name__, url_prefix="/features")


@features_bp.route("/welcome")
def welcome():
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")

    return render_template_string(
        """
    <!DOCTYPE html>
    <html>
    <head>
        <title>New Features - Employee Suite</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f6f6f7; }
            .container { max-width: 800px; margin: 0 auto; padding: 32px 24px; }
            .header { background: white; border-bottom: 1px solid #e1e3e5; padding: 16px 24px; margin-bottom: 32px; border-radius: 8px; }
            .back-btn { color: #008060; text-decoration: none; font-weight: 500; }
            .hero { text-align: center; margin-bottom: 48px; }
            .hero h1 { font-size: 32px; font-weight: 700; color: #202223; margin-bottom: 16px; }
            .hero p { font-size: 18px; color: #6d7175; }
            .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; }
            .feature { background: white; padding: 24px; border-radius: 8px; border: 1px solid #e1e3e5; }
            .feature h3 { font-size: 18px; font-weight: 600; color: #202223; margin-bottom: 12px; }
            .feature p { color: #6d7175; line-height: 1.6; }
            .badge { background: #008060; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; margin-right: 8px; }
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/dashboard?shop={{ shop }}&host={{ host }}" class="back-btn">← Back to Dashboard</a>
        </div>
        <div class="container">
            <div class="hero">
                <h1>🎉 New Features Available</h1>
                <p>Powerful new tools to grow your business</p>
            </div>
            <div class="features">
                <div class="feature">
                    <h3><span class="badge">NEW</span>CSV Exports</h3>
                    <p>Download your Orders, Inventory, and Revenue data as CSV files with date filtering. Perfect for accounting and analysis.</p>
                </div>
                <div class="feature">
                    <h3><span class="badge">NEW</span>Scheduled Reports</h3>
                    <p>Get automated reports delivered to your email or SMS at your preferred schedule. Never miss important updates.</p>
                </div>
                <div class="feature">
                    <h3><span class="badge">NEW</span>Comprehensive Dashboard</h3>
                    <p>View all three reports (Orders, Inventory, Revenue) in one unified dashboard with real-time updates.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """,
        shop=shop,
        host=host,
    )


@features_bp.route("/csv-exports")
def csv_exports():
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")

    return render_template_string(
        """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CSV Exports - Employee Suite</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f6f6f7; }
            .container { max-width: 800px; margin: 0 auto; padding: 32px 24px; }
            .header { background: white; border-bottom: 1px solid #e1e3e5; padding: 16px 24px; margin-bottom: 32px; border-radius: 8px; }
            .back-btn { color: #008060; text-decoration: none; font-weight: 500; }
            .card { background: white; padding: 24px; border-radius: 8px; border: 1px solid #e1e3e5; margin-bottom: 24px; }
            .card h3 { font-size: 18px; font-weight: 600; color: #202223; margin-bottom: 12px; }
            .btn { background: #008060; color: white; padding: 12px 24px; border: none; border-radius: 6px; text-decoration: none; display: inline-block; font-weight: 500; }
            .btn:hover { background: #006e52; }
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/dashboard?shop={{ shop }}&host={{ host }}" class="back-btn">← Back to Dashboard</a>
        </div>
        <div class="container">
            <h1 style="font-size: 28px; font-weight: 600; margin-bottom: 32px;">📥 CSV Exports</h1>

            <div class="card">
                <h3>📦 Orders Export</h3>
                <p style="color: #6d7175; margin-bottom: 16px;">Download all your orders with customer details, amounts, and status.</p>
                <a href="/api/export/orders?shop={{ shop }}" class="btn">Download Orders CSV</a>
            </div>

            <div class="card">
                <h3>📊 Inventory Export</h3>
                <p style="color: #6d7175; margin-bottom: 16px;">Export product inventory with stock levels, SKUs, and pricing.</p>
                <a href="/api/export/inventory-simple?shop={{ shop }}" class="btn">Download Inventory CSV</a>
            </div>

            <div class="card">
                <h3>💰 Revenue Export</h3>
                <p style="color: #6d7175; margin-bottom: 16px;">Get detailed revenue breakdown by product and time period.</p>
                <a href="/api/export/report?shop={{ shop }}" class="btn">Download Revenue CSV</a>
            </div>
        </div>
    </body>
    </html>
    """,
        shop=shop,
        host=host,
    )


@features_bp.route("/scheduled-reports")
def scheduled_reports():
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")
    success = request.args.get("success", "")
    error = request.args.get("error", "")

    return render_template_string(
        """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Scheduled Reports - Employee Suite</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f6f6f7; }
            .container { max-width: 800px; margin: 0 auto; padding: 32px 24px; }
            .header { background: white; border-bottom: 1px solid #e1e3e5; padding: 16px 24px; margin-bottom: 32px; border-radius: 8px; }
            .back-btn { color: #008060; text-decoration: none; font-weight: 500; }
            .card { background: white; padding: 24px; border-radius: 8px; border: 1px solid #e1e3e5; margin-bottom: 24px; }
            .card h3 { font-size: 18px; font-weight: 600; color: #202223; margin-bottom: 16px; }
            .form-group { margin-bottom: 16px; }
            .form-group label { display: block; font-size: 14px; font-weight: 500; color: #202223; margin-bottom: 6px; }
            .form-group select, .form-group input { width: 100%; padding: 10px 12px; border: 1px solid #e1e3e5; border-radius: 6px; font-size: 14px; }
            .btn { background: #008060; color: white; padding: 12px 24px; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; }
            .btn:hover { background: #006e52; }
            .btn-danger { background: #d72c0d; }
            .btn-danger:hover { background: #bf280a; }
            .success { background: #f0fdf4; border: 1px solid #86efac; padding: 12px 16px; border-radius: 6px; color: #166534; margin-bottom: 20px; }
            .error { background: #fff4f4; border: 1px solid #fecaca; padding: 12px 16px; border-radius: 6px; color: #d72c0d; margin-bottom: 20px; }
            .report-item { display: flex; justify-content: space-between; align-items: center; padding: 16px; border: 1px solid #e1e3e5; border-radius: 6px; margin-bottom: 12px; }
            .report-info { flex: 1; }
            .report-info h4 { font-size: 16px; font-weight: 600; color: #202223; margin-bottom: 4px; }
            .report-info p { font-size: 14px; color: #6d7175; }
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/dashboard?shop={{ shop }}&host={{ host }}" class="back-btn">← Back to Dashboard</a>
        </div>
        <div class="container">
            <h1 style="font-size: 28px; font-weight: 600; margin-bottom: 32px;">📅 Scheduled Reports</h1>

            {% if success %}
            <div class="success">✅ {{ success }}</div>
            {% endif %}
            
            {% if error %}
            <div class="error">❌ {{ error }}</div>
            {% endif %}

            <div class="card">
                <h3>Create New Schedule</h3>
                <form method="POST" action="/api/scheduled-reports/create">
                    <input type="hidden" name="shop" value="{{ shop }}">
                    <input type="hidden" name="host" value="{{ host }}">
                    
                    <div class="form-group">
                        <label>Report Type:</label>
                        <select name="report_type" required>
                            <option value="">Select report type...</option>
                            <option value="orders">Orders Report</option>
                            <option value="inventory">Inventory Report</option>
                            <option value="revenue">Revenue Report</option>
                            <option value="all">All Reports</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label>Frequency:</label>
                        <select name="frequency" required>
                            <option value="">Select frequency...</option>
                            <option value="daily">Daily</option>
                            <option value="weekly">Weekly</option>
                            <option value="monthly">Monthly</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label>Email Address:</label>
                        <input type="email" name="email" placeholder="your-email@example.com" required>
                    </div>
                    
                    <button type="submit" class="btn">Create Schedule</button>
                </form>
            </div>

            <div class="card">
                <h3>Your Scheduled Reports</h3>
                <div id="reports-list">
                    <p style="color: #6d7175; text-align: center; padding: 20px;">Loading your scheduled reports...</p>
                </div>
            </div>
        </div>

        <script>
            // Load existing scheduled reports
            fetch('/api/scheduled-reports/list')
                .then(r => r.json())
                .then(data => {
                    const container = document.getElementById('reports-list');
                    if (data.success && data.reports.length > 0) {
                        container.innerHTML = data.reports.map(report => `
                            <div class="report-item">
                                <div class="report-info">
                                    <h4>${report.report_type.charAt(0).toUpperCase() + report.report_type.slice(1)} Report</h4>
                                    <p>Frequency: ${report.frequency} • Email: ${report.delivery_email}</p>
                                    <p>Next delivery: ${report.next_send_at}</p>
                                </div>
                                <button class="btn btn-danger" onclick="deleteReport(${report.id})">Delete</button>
                            </div>
                        `).join('');
                    } else {
                        container.innerHTML = '<p style="color: #6d7175; text-align: center; padding: 20px;">No scheduled reports yet. Create one above to get started.</p>';
                    }
                })
                .catch(e => {
                    document.getElementById('reports-list').innerHTML = '<p style="color: #d72c0d; text-align: center; padding: 20px;">Error loading reports. Please refresh the page.</p>';
                });

            function deleteReport(reportId) {
                if (confirm('Are you sure you want to delete this scheduled report?')) {
                    fetch(`/api/scheduled-reports/delete/${reportId}`, { method: 'POST' })
                        .then(r => r.json())
                        .then(data => {
                            if (data.success) {
                                location.reload();
                            } else {
                                alert('Error deleting report: ' + data.error);
                            }
                        })
                        .catch(e => alert('Error deleting report. Please try again.'));
                }
            }
        </script>
    </body>
    </html>
    """,
        shop=shop,
        host=host,
        success=success,
        error=error,
    )


@features_bp.route("/dashboard")
def comprehensive_dashboard():
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")

    return render_template_string(
        """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Comprehensive Dashboard - Employee Suite</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f6f6f7; }
            .container { max-width: 1200px; margin: 0 auto; padding: 32px 24px; }
            .header { background: white; border-bottom: 1px solid #e1e3e5; padding: 16px 24px; margin-bottom: 32px; border-radius: 8px; }
            .back-btn { color: #008060; text-decoration: none; font-weight: 500; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 24px; }
            .card { background: white; padding: 24px; border-radius: 8px; border: 1px solid #e1e3e5; }
            .card h3 { font-size: 18px; font-weight: 600; color: #202223; margin-bottom: 16px; }
            .btn { background: #008060; color: white; padding: 8px 16px; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; margin-top: 12px; }
            .content { min-height: 200px; padding: 16px; background: #f9f9f9; border-radius: 6px; margin-bottom: 12px; font-family: monospace; font-size: 13px; }
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/dashboard?shop={{ shop }}&host={{ host }}" class="back-btn">← Back to Dashboard</a>
        </div>
        <div class="container">
            <h1 style="font-size: 28px; font-weight: 600; margin-bottom: 32px;">📊 Comprehensive Dashboard</h1>

            <div class="grid">
                <div class="card">
                    <h3>📦 Orders Overview</h3>
                    <div class="content" id="orders-content">Click "Load Orders" to view your order data...</div>
                    <button class="btn" onclick="loadOrders()">Load Orders</button>
                </div>

                <div class="card">
                    <h3>📊 Inventory Status</h3>
                    <div class="content" id="inventory-content">Click "Load Inventory" to view your inventory data...</div>
                    <button class="btn" onclick="loadInventory()">Load Inventory</button>
                </div>

                <div class="card">
                    <h3>💰 Revenue Report</h3>
                    <div class="content" id="revenue-content">Click "Load Revenue" to view your revenue data...</div>
                    <button class="btn" onclick="loadRevenue()">Load Revenue</button>
                </div>
            </div>
        </div>

        <script>
            function loadOrders() {
                document.getElementById('orders-content').innerHTML = 'Loading orders...';
                fetch('/api/process_orders?shop={{ shop }}')
                    .then(r => r.json())
                    .then(d => {
                        if (d.success) {
                            document.getElementById('orders-content').innerHTML = d.html || d.message || 'Orders loaded successfully';
                        } else {
                            document.getElementById('orders-content').innerHTML = 'Error: ' + (d.error || 'Failed to load orders');
                        }
                    })
                    .catch(e => {
                        document.getElementById('orders-content').innerHTML = 'Network error loading orders';
                    });
            }

            function loadInventory() {
                document.getElementById('inventory-content').innerHTML = 'Loading inventory...';
                fetch('/api/update_inventory?shop={{ shop }}')
                    .then(r => r.json())
                    .then(d => {
                        if (d.success) {
                            document.getElementById('inventory-content').innerHTML = d.html || d.message || 'Inventory loaded successfully';
                        } else {
                            document.getElementById('inventory-content').innerHTML = 'Error: ' + (d.error || 'Failed to load inventory');
                        }
                    })
                    .catch(e => {
                        document.getElementById('inventory-content').innerHTML = 'Network error loading inventory';
                    });
            }

            function loadRevenue() {
                document.getElementById('revenue-content').innerHTML = 'Loading revenue...';
                fetch('/api/generate_report?shop={{ shop }}')
                    .then(r => r.json())
                    .then(d => {
                        if (d.success) {
                            document.getElementById('revenue-content').innerHTML = d.html || d.message || 'Revenue loaded successfully';
                        } else {
                            document.getElementById('revenue-content').innerHTML = 'Error: ' + (d.error || 'Failed to load revenue');
                        }
                    })
                    .catch(e => {
                        document.getElementById('revenue-content').innerHTML = 'Network error loading revenue';
                    });
            }
        </script>
    </body>
    </html>
    """,
        shop=shop,
        host=host,
    )
