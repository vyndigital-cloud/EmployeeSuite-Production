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
        .faq-item {
            background: #ffffff;
            border: 1px solid #e1e3e5;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 16px;
            transition: box-shadow 0.15s;
        }
        .faq-item:hover {
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }
        .faq-question {
            font-size: 17px;
            font-weight: 600;
            color: #202223;
            margin-bottom: 12px;
        }
        .faq-answer {
            font-size: 14px;
            color: #6d7175;
            line-height: 1.6;
        }
        
        /* Mobile */
        @media (max-width: 768px) {
            .container { padding: 24px 16px; }
            .page-title { font-size: 24px; }
            .faq-item { padding: 20px; }
            .header-content { padding: 0 16px; height: 56px; }
        }
        @media (max-width: 480px) {
            .container { padding: 20px 12px; }
            .page-title { font-size: 20px; }
            .faq-item { padding: 16px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <a href="/" class="logo">
                <span>Employee Suite</span>
            </a>
        </div>
    </div>
    
    <div class="container">
        <h1 class="page-title">Frequently Asked Questions</h1>
        <p class="page-subtitle">Everything you need to know about Employee Suite</p>
        
        <div class="faq-item">
            <div class="faq-question">How does the free trial work?</div>
            <div class="faq-answer">You get 7 days of free access starting immediately when you sign up. No credit card required during trial. After 7 days, you need to subscribe to continue using the platform.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">How much does it cost?</div>
            <div class="faq-answer"><strong>Plan:</strong> $29 USD/month. No setup fees. Cancel anytime.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">What is the maximum capacity?</div>
            <div class="faq-answer">Our current infrastructure can comfortably support 50-100 active users. We're continuously scaling to accommodate growth and will expand capacity as needed to serve all customers.</div>
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
            <div class="faq-answer"><strong>7-Day Refund Policy:</strong> Monthly subscription fees ($29 USD) are refundable if requested within 7 days of payment, provided you have not used the platform features (order processing, inventory management, or revenue reports) after subscribing. To prevent abuse, refunds are limited to one per customer account. Email adam@golproductions.com within 7 days to request a refund. All refund requests are subject to verification.</div>
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
