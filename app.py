from flask import Flask, jsonify, render_template_string
import os
from order_processing import process_orders
from inventory import update_inventory
from reporting import generate_report

app = Flask(__name__)
app.config['ENV'] = os.getenv('FLASK_ENV', 'production')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False') == 'True'

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Employee Suite - Live Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; color: white; padding: 40px 20px; }
        .header h1 { font-size: 3em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .header p { font-size: 1.2em; opacity: 0.9; }
        .status { background: rgba(255,255,255,0.95); border-radius: 15px; padding: 20px; margin: 20px 0; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
        .status h2 { color: #28a745; margin-bottom: 10px; }
        .button-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin: 30px 0; }
        .action-btn { background: white; border: none; border-radius: 12px; padding: 30px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease; text-align: center; }
        .action-btn:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.2); }
        .action-btn h3 { color: #667eea; font-size: 1.5em; margin-bottom: 10px; }
        .action-btn p { color: #666; margin-bottom: 20px; }
        .btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px 30px; border-radius: 25px; font-size: 1em; cursor: pointer; transition: all 0.3s ease; }
        .btn:hover { transform: scale(1.05); }
        #output { background: white; border-radius: 12px; padding: 30px; margin: 20px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); min-height: 200px; max-height: 500px; overflow-y: auto; white-space: pre-wrap; }
        .success { color: #28a745; font-weight: bold; }
        .error { color: #dc3545; font-weight: bold; }
        .loading { display: inline-block; width: 20px; height: 20px; border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .footer { text-align: center; color: white; padding: 20px; margin-top: 40px; opacity: 0.8; }
        .report-item { padding: 15px; border-bottom: 1px solid #eee; }
        .report-item strong { color: #667eea; }
        .total { font-size: 1.3em; color: #28a745; margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 8px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Employee Suite</h1>
            <p>Automated E-Commerce Management Platform</p>
        </div>
        <div class="status">
            <h2>✅ System Online</h2>
            <p>Connected to Shopify. Ready to automate your business.</p>
        </div>
        <div class="button-grid">
            <div class="action-btn">
                <h3>📦 Orders</h3>
                <p>Process pending orders from Shopify</p>
                <button class="btn" onclick="processOrders()">Process Orders</button>
            </div>
            <div class="action-btn">
                <h3>📊 Inventory</h3>
                <p>Track stock levels and get low-stock alerts</p>
                <button class="btn" onclick="updateInventory()">Check Inventory</button>
            </div>
            <div class="action-btn">
                <h3>💰 Reports</h3>
                <p>Generate revenue and profit reports</p>
                <button class="btn" onclick="generateReport()">Generate Report</button>
            </div>
        </div>
        <div id="output">
            <p style="color: #999; text-align: center; padding: 60px 0;">Click any button above to start automation...</p>
        </div>
        <div class="footer">
            <p>Powered by Employee Suite v1.0 | Real-time Shopify Integration</p>
        </div>
    </div>
    <script>
        function showLoading() {
            document.getElementById('output').innerHTML = '<div style="text-align: center; padding: 80px 0;"><div class="loading"></div><p style="margin-top: 20px; color: #999;">Processing...</p></div>';
        }
        function processOrders() {
            showLoading();
            fetch('/api/process_orders').then(response => response.json()).then(data => {
                document.getElementById('output').innerHTML = '<h3 class="success">✅ Orders Processed</h3><p style="margin-top: 10px; font-size: 1.1em;">' + (data.message || data.error) + '</p>';
            }).catch(error => {
                document.getElementById('output').innerHTML = '<h3 class="error">❌ Error</h3><p>' + error + '</p>';
            });
        }
        function updateInventory() {
            showLoading();
            fetch('/api/update_inventory').then(response => response.json()).then(data => {
                document.getElementById('output').innerHTML = '<h3 class="success">✅ Inventory Updated</h3><p style="margin-top: 10px; font-size: 1.1em;">' + (data.message || data.error) + '</p>';
            }).catch(error => {
                document.getElementById('output').innerHTML = '<h3 class="error">❌ Error</h3><p>' + error + '</p>';
            });
        }
        function generateReport() {
            showLoading();
            fetch('/api/generate_report').then(response => response.text()).then(html => {
                document.getElementById('output').innerHTML = html;
            }).catch(error => {
                document.getElementById('output').innerHTML = '<h3 class="error">❌ Error</h3><p>' + error + '</p>';
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(DASHBOARD_HTML)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "Employee Suite", "version": "1.0"})

@app.route('/api/process_orders', methods=['GET', 'POST'])
def api_process_orders():
    try:
        result = process_orders()
        return jsonify({"message": result, "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/update_inventory', methods=['GET', 'POST'])
def api_update_inventory():
    try:
        result = update_inventory()
        return jsonify({"message": result, "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/generate_report', methods=['GET', 'POST'])
def api_generate_report():
    try:
        data = generate_report()
        html = '<style>.report-item{padding:15px;border-bottom:1px solid #eee}.report-item strong{color:#667eea}.total{font-size:1.5em;color:#28a745;margin-top:20px;padding:20px;background:#f8f9fa;border-radius:8px}</style><h3 class="success">📊 Revenue Report</h3>'
        for product in data['products']:
            html += f'<div class="report-item"><strong>{product["name"]}</strong> - Stock: {product["stock"]} - Revenue: {product["revenue"]}</div>'
        html += f'<div class="total">💰 Total Revenue: {data["total_revenue"]}<br>📦 Total Products: {data["total_products"]}</div>'
        return html
    except Exception as e:
        return f"<h3 class='error'>❌ Error: {str(e)}</h3>", 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found", "status": 404}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error", "status": 500}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
