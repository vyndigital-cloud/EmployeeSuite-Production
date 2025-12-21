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
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #ffffff;
            color: #171717;
            line-height: 1.5;
        }
        .header { background: #fff; border-bottom: 1px solid #f0f0f0; }
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 32px;
            height: 72px;
            display: flex;
            align-items: center;
        }
        .logo { font-size: 17px; font-weight: 500; color: #171717; text-decoration: none; display: flex; align-items: center; gap: 10px; letter-spacing: -0.3px; }
        .container { max-width: 800px; margin: 0 auto; padding: 64px 32px; }
        .page-title { font-size: 32px; font-weight: 600; color: #0a0a0a; margin-bottom: 8px; letter-spacing: -0.5px; }
        .page-subtitle { font-size: 16px; color: #737373; margin-bottom: 40px; }
        .content { background: #fff; border: 1px solid #f0f0f0; border-radius: 12px; padding: 40px; line-height: 1.7; }
        h2 { font-size: 20px; font-weight: 600; color: #0a0a0a; margin: 40px 0 16px; }
        p { margin: 16px 0; color: #525252; font-size: 15px; }
        
        /* Mobile */
        @media (max-width: 768px) {
            .container { padding: 40px 24px; }
            .page-title { font-size: 26px; }
            .content { padding: 32px 24px; }
            h2 { font-size: 18px; }
            .header-content { padding: 0 24px; height: 64px; }
        }
        @media (max-width: 480px) {
            .container { padding: 32px 20px; }
            .page-title { font-size: 24px; }
            .content { padding: 24px 20px; }
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
