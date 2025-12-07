from flask import Blueprint, render_template_string

faq_bp = Blueprint('faq', __name__)

FAQ_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>FAQ - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
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
        .page-title { font-size: 32px; font-weight: 700; color: #171717; margin-bottom: 8px; }
        .page-subtitle { font-size: 16px; color: #737373; margin-bottom: 40px; }
        .faq-item {
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 16px;
        }
        .faq-question {
            font-size: 18px;
            font-weight: 600;
            color: #171717;
            margin-bottom: 12px;
        }
        .faq-answer {
            font-size: 15px;
            color: #525252;
            line-height: 1.7;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <a href="/" class="logo">Employee Suite v1</a>
        </div>
    </div>
    
    <div class="container">
        <h1 class="page-title">Frequently Asked Questions</h1>
        <p class="page-subtitle">Everything you need to know about Employee Suite</p>
        
        <div class="faq-item">
            <div class="faq-question">How does the free trial work?</div>
            <div class="faq-answer">You get 2 days of free access starting immediately when you sign up. No credit card required during trial. After 2 days, you need to subscribe to continue using the platform.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">How much does it cost?</div>
            <div class="faq-answer">$1,000 one-time setup fee + $500/month subscription. Cancel anytime.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">How do I connect my Shopify store?</div>
            <div class="faq-answer">Go to Settings → Connect Shopify Store. You can connect manually by entering your store URL and Admin API access token, or use the OAuth flow if installing from the Shopify App Store.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">Can I cancel anytime?</div>
            <div class="faq-answer">Yes! Go to Settings → Subscription → Cancel Subscription. You'll retain access until the end of your current billing period. No questions asked.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">What happens if my payment fails?</div>
            <div class="faq-answer">You'll receive an email notification. Your account will be suspended if payment isn't received within 3 days. Update your payment method to restore access.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">Do you offer refunds?</div>
            <div class="faq-answer">Refund requests are handled on a case-by-case basis. Email us at adam@golproductions.com within 7 days of purchase to request a refund. We'll review your request and respond within 24 hours.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">How do I get support?</div>
            <div class="faq-answer">Email adam@golproductions.com. We respond within 24 hours.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">Can I use this with multiple stores?</div>
            <div class="faq-answer">Currently one store per account. Multi-store support coming soon.</div>
        </div>
    </div>
</body>
</html>
'''

@faq_bp.route('/faq')
def faq():
    return render_template_string(FAQ_HTML)
