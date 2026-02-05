"""
Simple test endpoint to verify app is accessible from Shopify
"""
from flask import Blueprint, jsonify, request

test_bp = Blueprint('test', __name__)

@test_bp.route('/ping')
def ping():
    """Simple ping endpoint to test connectivity"""
    return jsonify({
        'status': 'ok',
        'message': 'Employee Suite is running',
        'embedded': bool(request.args.get('embedded')),
        'shop': request.args.get('shop', 'none'),
        'host': request.args.get('host', 'none')
    })

@test_bp.route('/test-embed')
def test_embed():
    """Test page for embedded app"""
    from flask import render_template_string
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Employee Suite - Test</title>
        <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
    </head>
    <body style="font-family: sans-serif; padding: 40px; text-align: center;">
        <h1>✅ Employee Suite is Working!</h1>
        <p>Shop: {{ shop }}</p>
        <p>Host: {{ host }}</p>
        <p>If you see this, the app is loading correctly.</p>
        <a href="/" style="display: inline-block; margin-top: 20px; padding: 12px 24px; background: #008060; color: white; text-decoration: none; border-radius: 6px;">Go to Dashboard</a>
    </body>
    </html>
    """, shop=shop, host=host)
