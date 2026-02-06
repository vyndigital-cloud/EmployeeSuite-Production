"""
OAuth Diagnostics Tool
Helps diagnose OAuth flow issues by providing detailed information about the configuration
"""

import os
from flask import Blueprint, render_template_string, request
from urllib.parse import quote

diagnostics_bp = Blueprint('oauth_diagnostics', __name__)

@diagnostics_bp.route('/oauth/diagnostics')
def diagnostics():
    """Display OAuth configuration diagnostics"""
    
    # Get environment variables
    api_key = os.getenv("SHOPIFY_API_KEY", "NOT_SET")
    api_secret = os.getenv("SHOPIFY_API_SECRET", "NOT_SET")
    redirect_uri = os.getenv(
        "SHOPIFY_REDIRECT_URI",
        "https://employeesuite-production.onrender.com/auth/callback"
    ).strip().strip('"').strip("'")
    
    # Mask sensitive data
    api_key_display = f"{api_key[:8]}..." if api_key != "NOT_SET" and len(api_key) > 8 else "NOT_SET"
    api_secret_display = "SET" if api_secret != "NOT_SET" else "NOT_SET"
    
    # Get shop parameter
    shop = request.args.get('shop', 'yourstore.myshopify.com')
    
    # Normalize shop
    shop_normalized = shop.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip()
    if not shop_normalized.endswith(".myshopify.com") and "." not in shop_normalized:
        shop_normalized = f"{shop_normalized}.myshopify.com"
    
    # Build OAuth URL
    scopes = "read_orders,read_products,read_inventory"
    auth_url = f"https://{shop_normalized}/admin/oauth/authorize"
    
    params = {
        "client_id": api_key,
        "scope": scopes,
        "redirect_uri": redirect_uri,
        "state": shop_normalized,
    }
    
    query_string = "&".join([f"{k}={quote(str(v), safe='')}" for k, v in params.items()])
    full_auth_url = f"{auth_url}?{query_string}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>OAuth Diagnostics - Employee Suite</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                max-width: 900px;
                margin: 40px auto;
                padding: 20px;
                background: #f6f6f7;
            }}
            .card {{
                background: white;
                padding: 24px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            h1 {{
                font-size: 24px;
                margin-bottom: 8px;
                color: #202223;
            }}
            h2 {{
                font-size: 18px;
                margin-top: 24px;
                margin-bottom: 12px;
                color: #202223;
                border-bottom: 2px solid #e1e3e5;
                padding-bottom: 8px;
            }}
            .status {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                margin-left: 8px;
            }}
            .status.ok {{
                background: #d1f7c4;
                color: #108043;
            }}
            .status.error {{
                background: #fed3d1;
                color: #d72c0d;
            }}
            .config-item {{
                margin: 12px 0;
                padding: 12px;
                background: #f6f6f7;
                border-radius: 4px;
                font-family: 'Monaco', 'Courier New', monospace;
                font-size: 13px;
            }}
            .label {{
                font-weight: 600;
                color: #6d7175;
                display: block;
                margin-bottom: 4px;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 12px;
                text-transform: uppercase;
            }}
            .value {{
                color: #202223;
                word-break: break-all;
            }}
            .btn {{
                background: #008060;
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                text-decoration: none;
                font-weight: 500;
                display: inline-block;
                margin-top: 12px;
            }}
            .btn:hover {{
                background: #006e52;
            }}
            .warning {{
                background: #fff4e6;
                border-left: 4px solid #ff9800;
                padding: 12px;
                margin: 12px 0;
                border-radius: 4px;
            }}
            .info {{
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
                padding: 12px;
                margin: 12px 0;
                border-radius: 4px;
            }}
            .checklist {{
                list-style: none;
                padding: 0;
            }}
            .checklist li {{
                padding: 8px 0;
                border-bottom: 1px solid #e1e3e5;
            }}
            .checklist li:last-child {{
                border-bottom: none;
            }}
            input[type="text"] {{
                width: 100%;
                padding: 10px;
                border: 1px solid #c9cccf;
                border-radius: 4px;
                font-size: 14px;
                margin-top: 8px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🔍 OAuth Diagnostics</h1>
            <p style="color: #6d7175;">Diagnose OAuth configuration and test the flow</p>
        </div>

        <div class="card">
            <h2>Environment Configuration</h2>
            
            <div class="config-item">
                <span class="label">Shopify API Key</span>
                <span class="value">{api_key_display}</span>
                <span class="status {'ok' if api_key != 'NOT_SET' else 'error'}">
                    {'✓ SET' if api_key != 'NOT_SET' else '✗ NOT SET'}
                </span>
            </div>

            <div class="config-item">
                <span class="label">Shopify API Secret</span>
                <span class="value">{api_secret_display}</span>
                <span class="status {'ok' if api_secret != 'NOT_SET' else 'error'}">
                    {'✓ SET' if api_secret != 'NOT_SET' else '✗ NOT SET'}
                </span>
            </div>

            <div class="config-item">
                <span class="label">Redirect URI</span>
                <span class="value">{redirect_uri}</span>
                <span class="status ok">✓ SET</span>
            </div>

            <div class="config-item">
                <span class="label">Scopes</span>
                <span class="value">{scopes}</span>
            </div>
        </div>

        <div class="card">
            <h2>Test OAuth Flow</h2>
            
            <form method="get" action="/oauth/diagnostics">
                <label class="label" for="shop">Shop Domain</label>
                <input type="text" id="shop" name="shop" value="{shop}" 
                       placeholder="yourstore.myshopify.com">
            </form>

            <div class="info" style="margin-top: 16px;">
                <strong>📋 Normalized Shop:</strong> {shop_normalized}
            </div>

            <div class="config-item" style="margin-top: 16px;">
                <span class="label">Generated OAuth URL</span>
                <span class="value" style="font-size: 11px;">{full_auth_url}</span>
            </div>

            <a href="{full_auth_url}" class="btn" target="_blank">
                🚀 Test OAuth Flow
            </a>
        </div>

        <div class="card">
            <h2>Pre-Flight Checklist</h2>
            
            <div class="warning">
                <strong>⚠️ Important:</strong> Before testing OAuth, verify these items in your Shopify Partners Dashboard
            </div>

            <ul class="checklist">
                <li>✓ App is created in Shopify Partners Dashboard</li>
                <li>✓ Redirect URI matches exactly: <code>{redirect_uri}</code></li>
                <li>✓ Required scopes are enabled in App Setup → Access Scopes</li>
                <li>✓ App is installed on a development store or test store</li>
                <li>✓ Store is not password-protected (or you're logged in)</li>
            </ul>
        </div>

        <div class="card">
            <h2>Common Issues</h2>
            
            <div class="warning">
                <strong>Issue:</strong> "redirect_uri is not whitelisted"<br>
                <strong>Solution:</strong> Ensure the redirect URI in Partners Dashboard exactly matches: {redirect_uri}
            </div>

            <div class="warning" style="margin-top: 12px;">
                <strong>Issue:</strong> Callback receives empty parameters<br>
                <strong>Solution:</strong> This is usually caused by bots/crawlers. Check logs for legitimate OAuth redirects from Shopify.
            </div>

            <div class="warning" style="margin-top: 12px;">
                <strong>Issue:</strong> "Missing required parameters"<br>
                <strong>Solution:</strong> Shopify didn't complete the redirect. Check if the store authorized the app.
            </div>
        </div>

        <div class="card">
            <h2>Next Steps</h2>
            
            <ol>
                <li>Click "Test OAuth Flow" button above</li>
                <li>You should be redirected to Shopify's authorization page</li>
                <li>Click "Install app" or "Authorize" on Shopify's page</li>
                <li>You should be redirected back to /auth/callback with OAuth parameters</li>
                <li>Check your application logs for the OAuth callback details</li>
            </ol>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html)
