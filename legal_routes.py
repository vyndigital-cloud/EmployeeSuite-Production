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
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 50%, #f0f4f8 100%);
            background-attachment: fixed;
            color: #171717;
            line-height: 1.6;
        }
        .header { 
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(0, 0, 0, 0.06);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 32px;
            height: 72px;
            display: flex;
            align-items: center;
        }
        .logo { font-size: 18px; font-weight: 600; color: #0a0a0a; text-decoration: none; display: flex; align-items: center; gap: 10px; letter-spacing: -0.4px; }
        .container { max-width: 800px; margin: 0 auto; padding: 80px 32px; }
        .page-title { font-size: 48px; font-weight: 700; color: #0a0a0a; margin-bottom: 12px; letter-spacing: -1px; line-height: 1.1; }
        .page-subtitle { font-size: 18px; color: #64748b; margin-bottom: 56px; }
        .content { 
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 1) 100%);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-radius: 20px;
            padding: 48px;
            line-height: 1.8;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
        }
        h2 { font-size: 24px; font-weight: 700; color: #0a0a0a; margin: 48px 0 20px; letter-spacing: -0.4px; }
        p { margin: 20px 0; color: #475569; font-size: 15px; }
        
        /* Mobile */
        @media (max-width: 768px) {
            .container { padding: 48px 24px; }
            .page-title { font-size: 36px; }
            .content { padding: 40px 32px; }
            h2 { font-size: 20px; }
            .header-content { padding: 0 24px; height: 64px; }
        }
        @media (max-width: 480px) {
            .container { padding: 40px 20px; }
            .page-title { font-size: 28px; }
            .content { padding: 32px 24px; }
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
