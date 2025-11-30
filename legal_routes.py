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
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto; background: #f8f9fa; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #667eea; margin-bottom: 10px; font-size: 2em; }
        .updated { color: #999; font-size: 0.9em; margin-bottom: 30px; }
        h2 { color: #333; margin-top: 30px; margin-bottom: 15px; font-size: 1.3em; }
        p { line-height: 1.8; color: #666; margin-bottom: 15px; white-space: pre-wrap; }
        a { color: #667eea; text-decoration: none; }
        .back { display: inline-block; margin-bottom: 20px; color: #667eea; font-weight: 500; }
        .back:hover { text-decoration: underline; }
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
