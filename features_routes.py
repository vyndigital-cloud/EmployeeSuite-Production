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
            .header { background: white; border-bottom: 1px solid #e1e3e5; padding: 16px 24px; margin-bottom: 32px; }
            .back-btn { color: #008060; text-decoration: none; font-weight: 500; }
            .hero { text-align: center; margin-bottom: 48px; }
            .hero h1 { font-size: 32px; font-weight: 700; color: #202223; margin-bottom: 16px; }
            .hero p { font-size: 18px; color: #6d7175; }
            .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; }
            .feature { background: white; padding: 24px; border-radius: 8px; border: 1px solid #e1e3e5; }
            .feature h3 { font-size: 18px; font-weight: 600; color: #202223; margin-bottom: 12px; }
            .feature p { color: #6d7175; line-height: 1.6; }
            .badge { background: #008060; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
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
                    <h3><span class="badge">NEW</span> CSV Exports</h3>
                    <p>Download your Orders, Inventory, and Revenue data as CSV files with date filtering. Perfect for accounting and analysis.</p>
                </div>
                <div class="feature">
                    <h3><span class="badge">NEW</span> Scheduled Reports</h3>
                    <p>Get automated reports delivered to your email or SMS at your preferred schedule. Never miss important updates.</p>
                </div>
                <div class="feature">
                    <h3><span class="badge">NEW</span> Comprehensive Dashboard</h3>
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
            .header { background: white; border-bottom: 1px solid #e1e3e5; padding: 16px 24px; margin-bottom: 32px; }
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
                <a href="/api/export/orders" class="btn">Download Orders CSV</a>
            </div>

            <div class="card">
                <h3>📊 Inventory Export</h3>
                <p style="color: #6d7175; margin-bottom: 16px;">Export product inventory with stock levels, SKUs, and pricing.</p>
                <a href="/api/export/inventory-simple" class="btn">Download Inventory CSV</a>
            </div>

            <div class="card">
                <h3>💰 Revenue Export</h3>
                <p style="color: #6d7175; margin-bottom: 16px;">Get detailed revenue breakdown by product and time period.</p>
                <a href="/api/export/report" class="btn">Download Revenue CSV</a>
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
            .header { background: white; border-bottom: 1px solid #e1e3e5; padding: 16px 24px; margin-bottom: 32px; }
            .back-btn { color: #008060; text-decoration: none; font-weight: 500; }
            .card { background: white; padding: 24px; border-radius: 8px; border: 1px solid #e1e3e5; }
            .coming-soon { text-align: center; padding: 48px 24px; }
            .coming-soon h2 { font-size: 24px; font-weight: 600; color: #202223; margin-bottom: 16px; }
            .coming-soon p { color: #6d7175; font-size: 16px; line-height: 1.6; }
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/dashboard?shop={{ shop }}&host={{ host }}" class="back-btn">← Back to Dashboard</a>
        </div>
        <div class="container">
            <h1 style="font-size: 28px; font-weight: 600; margin-bottom: 32px;">📅 Scheduled Reports</h1>

            <div class="card">
                <div class="coming-soon">
                    <h2>🚀 Coming Soon</h2>
                    <p>Automated report delivery via email and SMS is in development. You'll be able to schedule daily, weekly, or monthly reports to stay updated on your store performance.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """,
        shop=shop,
        host=host,
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
            .header { background: white; border-bottom: 1px solid #e1e3e5; padding: 16px 24px; margin-bottom: 32px; }
            .back-btn { color: #008060; text-decoration: none; font-weight: 500; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; }
            .card { background: white; padding: 24px; border-radius: 8px; border: 1px solid #e1e3e5; }
            .card h3 { font-size: 18px; font-weight: 600; color: #202223; margin-bottom: 16px; }
            .btn { background: #008060; color: white; padding: 8px 16px; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
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
                    <div id="orders-content">Loading orders...</div>
                    <button class="btn" onclick="loadOrders()">Refresh Orders</button>
                </div>

                <div class="card">
                    <h3>📊 Inventory Status</h3>
                    <div id="inventory-content">Loading inventory...</div>
                    <button class="btn" onclick="loadInventory()">Refresh Inventory</button>
                </div>

                <div class="card">
                    <h3>💰 Revenue Report</h3>
                    <div id="revenue-content">Loading revenue...</div>
                    <button class="btn" onclick="loadRevenue()">Refresh Revenue</button>
                </div>
            </div>
        </div>

        <script>
            function loadOrders() {
                document.getElementById('orders-content').innerHTML = 'Loading...';
                fetch('/api/process_orders?shop={{ shop }}')
                    .then(r => r.json())
                    .then(d => {
                        document.getElementById('orders-content').innerHTML = d.html || d.message || 'No data';
                    })
                    .catch(e => {
                        document.getElementById('orders-content').innerHTML = 'Error loading orders';
                    });
            }

            function loadInventory() {
                document.getElementById('inventory-content').innerHTML = 'Loading...';
                fetch('/api/update_inventory?shop={{ shop }}')
                    .then(r => r.json())
                    .then(d => {
                        document.getElementById('inventory-content').innerHTML = d.html || d.message || 'No data';
                    })
                    .catch(e => {
                        document.getElementById('inventory-content').innerHTML = 'Error loading inventory';
                    });
            }

            function loadRevenue() {
                document.getElementById('revenue-content').innerHTML = 'Loading...';
                fetch('/api/generate_report?shop={{ shop }}')
                    .then(r => r.json())
                    .then(d => {
                        document.getElementById('revenue-content').innerHTML = d.html || d.message || 'No data';
                    })
                    .catch(e => {
                        document.getElementById('revenue-content').innerHTML = 'Error loading revenue';
                    });
            }

            // Auto-load on page load
            loadOrders();
            loadInventory();
            loadRevenue();
        </script>
    </body>
    </html>
    """,
        shop=shop,
        host=host,
    )
