from flask import Blueprint, render_template_string

legal_bp = Blueprint('legal', __name__)

with open('privacy_policy.txt', 'r') as f:
    PRIVACY_TEXT = f.read()

with open('terms_of_service.txt', 'r') as f:
    TERMS_TEXT = f.read()

LEGAL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }} - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f6f6f7;
            color: #202223;
            line-height: 1.5;
        }
        .header { 
            background: #ffffff;
            border-bottom: 1px solid #e1e3e5;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
            height: 64px;
            display: flex;
            align-items: center;
        }
        .logo { font-size: 16px; font-weight: 600; color: #202223; text-decoration: none; display: flex; align-items: center; gap: 10px; letter-spacing: -0.2px; }
        .container { max-width: 800px; margin: 0 auto; padding: 32px 24px; }
        .page-title { font-size: 28px; font-weight: 600; color: #202223; margin-bottom: 8px; letter-spacing: -0.3px; }
        .page-subtitle { font-size: 15px; color: #6d7175; margin-bottom: 32px; }
        .content { 
            background: #ffffff;
            border: 1px solid #e1e3e5;
            border-radius: 8px;
            padding: 32px;
            line-height: 1.6;
        }
        h2 { font-size: 20px; font-weight: 600; color: #202223; margin: 32px 0 16px; }
        p { margin: 16px 0; color: #6d7175; font-size: 14px; }
        
        /* Mobile */
        @media (max-width: 768px) {
            .container { padding: 24px 16px; }
            .page-title { font-size: 24px; }
            .content { padding: 24px; }
            h2 { font-size: 18px; }
            .header-content { padding: 0 16px; height: 56px; }
        }
        @media (max-width: 480px) {
            .container { padding: 20px 12px; }
            .page-title { font-size: 20px; }
            .content { padding: 20px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <a href="/" class="logo">
                <span style="font-size: 20px;">🚀</span>
                <span>Employee Suite</span>
            </a>
        </div>
    </div>
    <div class="container">
        <h1 class="page-title">{{ title }}</h1>
        <div class="content">{{ content|safe }}</div>
    </div>
</body>
</html>
"""

@legal_bp.route('/privacy')
def privacy():
    content = PRIVACY_TEXT.replace('\n\n', '</p><p>').replace('\n', '<br>')
    content = f'<p>{content}</p>'
    return render_template_string(LEGAL_HTML, title="Privacy Policy", content=content)

@legal_bp.route('/terms')
def terms():
    content = TERMS_TEXT.replace('\n\n', '</p><p>').replace('\n', '<br>')
    content = f'<p>{content}</p>'
    return render_template_string(LEGAL_HTML, title="Terms of Service", content=content)
