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
        .content {
            background: #ffffff;
            border: 1px solid #e1e3e5;
            border-radius: 8px;
            padding: 32px;
            line-height: 1.6;
        }
        h2 { font-size: 20px; font-weight: 600; color: #202223; margin: 32px 0 16px; }
        h2:first-child { margin-top: 0; }
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
                <span>Employee Suite</span>
            </a>
        </div>
    </div>

    <div class="container">
        <h1 class="page-title">Frequently Asked Questions</h1>
        <p class="page-subtitle">Everything you need to know about Employee Suite</p>

        <div class="content">
            <h2>How does the free trial work?</h2>
            <p>You get 7 days of free access starting immediately when you sign up. No credit card required during trial. After 7 days, you need to subscribe to continue using the platform.</p>

            <h2>How much does it cost?</h2>
            <p><strong>Plan:</strong> $99 USD/month. No setup fees. Cancel anytime.</p>

            <h2>What is the maximum capacity?</h2>
            <p>Our current infrastructure can comfortably support 50-100 active users. We're continuously scaling to accommodate growth and will expand capacity as needed to serve all customers.</p>

            <h2>How do I connect my Shopify store?</h2>
            <p>Go to Settings → Connect Shopify Store. You can connect manually by entering your store URL and Admin API access token, or use the OAuth flow if installing from the Shopify App Store.</p>

            <h2>Can I cancel anytime?</h2>
            <p>Yes! Go to Settings → Subscription → Cancel Subscription. You'll retain access until the end of your current billing period. No questions asked.</p>

            <h2>What happens if my payment fails?</h2>
            <p>You'll receive an email notification. Your account will be suspended if payment isn't received within 3 days. Update your payment method to restore access.</p>

            <h2>Do you offer refunds?</h2>
            <p><strong>7-Day Refund Policy:</strong> Monthly subscription fees ($99 USD) are refundable if requested within 7 days of payment, provided you have not used the platform features (order processing, inventory management, or revenue reports) after subscribing. To prevent abuse, refunds are limited to one per customer account. Email adam@golproductions.com within 7 days to request a refund. All refund requests are subject to verification.</p>

            <h2>How do I get support?</h2>
            <p>Email adam@golproductions.com. We respond within 24 hours.</p>

            <h2>Can I use this with multiple stores?</h2>
            <p>Currently one store per account. Multi-store support coming soon.</p>
        </div>
    </div>
</body>
</html>
'''

@faq_bp.route('/faq')
def faq():
    return render_template_string(FAQ_HTML)
