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
        <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #fafafa;
            color: #171717;
        }
        .header { background: #fff; border-bottom: 1px solid #e5e5e5; }
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
            height: 64px;
            display: flex;
            align-items: center;
        }
        .logo { font-size: 18px; font-weight: 600; color: #171717; text-decoration: none; }
        .container { max-width: 800px; margin: 0 auto; padding: 48px 24px; }
        .page-title { font-size: 32px; font-weight: 700; color: #171717; margin-bottom: 32px; }
        .content { background: #fff; border: 1px solid #e5e5e5; border-radius: 16px; padding: 32px; line-height: 1.8; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05); }
        h2 { font-size: 20px; font-weight: 600; color: #171717; margin: 32px 0 16px; }
        p { margin: 16px 0; color: #525252; font-size: 15px; }
        
        /* Mobile Responsive */
        @media (max-width: 768px) {
            .container { padding: 32px 16px; }
            .page-title { font-size: 26px; }
            .content { padding: 24px; }
            h2 { font-size: 18px; }
            p { font-size: 14px; }
            .header-content { padding: 0 16px; }
        }
        @media (max-width: 480px) {
            .page-title { font-size: 24px; }
            .content { padding: 20px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back">← Back to Home</a>
        <h1>{{ title }}</h1>
        <div>{{ content|safe }}</div>
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
