
import logging
import sys
import os
from unittest.mock import MagicMock
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(os.getcwd())

# ------------------------------------------------------------------
# MOCKING INFRASTRUCTURE
# ------------------------------------------------------------------
captured_emails = []

class MockSendGridClient:
    def __init__(self, api_key=None):
        self.api_key = api_key

    def send(self, message):
        # Unwrap SendGrid Mail object
        
        # Helper to extract content
        html_content = ""
        # The SendGrid Mail object structure can vary, but usually has .content which is a list
        if hasattr(message, 'content') and message.content:
            for c in message.content:
                if c.type == 'text/html':
                    html_content = c.value
                    break
        
        # Helper to extract to_email
        to_email = "Unknown"
        # The Mail object structure is complex. We try to grab the first recipient.
        if hasattr(message, 'personalizations') and message.personalizations:
            # We access the underlying structure if possible
            try:
                # This depends on how sendgrid-python constructs objects. 
                # It often holds a list of Personalization objects.
                p = message.personalizations[0]
                if hasattr(p, 'tos') and p.tos:
                    to_email = p.tos[0]['email']
            except Exception:
                to_email = "unknown@test.com"
        
        # If accessing object attributes fails (dynamic attributes), try specific properties
        if not html_content and hasattr(message, 'get'):
             # Fallback if it's a dict-like object (unlikely for the object itself but possible)
             pass

        logger.info(f"CAPTURED EMAIL: {message.subject}")
        captured_emails.append({
            "to": to_email,
            "subject": message.subject,
            "html": html_content
        })
        
        response = MagicMock()
        response.status_code = 202
        return response

import email_service

# Monkey patch SendGridAPIClient in the email_service module
email_service.SendGridAPIClient = MockSendGridClient
# Ensure SENDGRID_AVAILABLE is True so it doesn't just log and return
email_service.SENDGRID_AVAILABLE = True

# Now import the functions wrapper or just call them from module
from email_service import (
    send_trial_expiry_warning,
    send_welcome_email,
    send_payment_success,
    send_cancellation_email,
    send_password_reset_email,
    send_report_email,
    send_payment_failed
)

def test_emails():
    test_email = "test@example.com"
    logger.info(f"Starting email tests. Recipient: {test_email}")

    # 1. Welcome Email
    logger.info("--- Testing Welcome Email ---")
    send_welcome_email(test_email)

    # 2. Trial Expiry Warning
    logger.info("--- Testing Trial Expiry Warning ---")
    send_trial_expiry_warning(test_email, 3)

    # 3. Payment Success
    logger.info("--- Testing Payment Success ---")
    send_payment_success(test_email)

    # 4. Cancellation Email
    logger.info("--- Testing Cancellation Email ---")
    send_cancellation_email(test_email)

    # 5. Password Reset
    logger.info("--- Testing Password Reset ---")
    send_password_reset_email(test_email, "dummy-reset-token-12345")

    # 6. Payment Failed
    logger.info("--- Testing Payment Failed ---")
    send_payment_failed(test_email)

    # 7. Report Email
    logger.info("--- Testing Report Email ---")
    dummy_report = """
    <table border="1" cellpadding="10" style="border-collapse: collapse; width: 100%; border: 1px solid #e5e7eb;">
        <tr style="background: #f9fafb;">
            <th style="padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb;">Metric</th>
            <th style="padding: 12px; text-align: right; border-bottom: 1px solid #e5e7eb;">Value</th>
        </tr>
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">Total Revenue</td>
            <td style="padding: 12px; text-align: right; border-bottom: 1px solid #e5e7eb; font-weight: bold;">$12,450.00</td>
        </tr>
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">Total Orders</td>
            <td style="padding: 12px; text-align: right; border-bottom: 1px solid #e5e7eb;">142</td>
        </tr>
        <tr>
            <td style="padding: 12px;">Avg. Order Value</td>
            <td style="padding: 12px; text-align: right;">$87.68</td>
        </tr>
    </table>
    """
    send_report_email(test_email, "Weekly Performance", dummy_report)

    # Generate HTML Preview
    preview_path = "email_previews.html"
    with open(preview_path, "w") as f:
        f.write("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Employee Suite - Email Previews</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 40px; background: #f3f4f6; color: #1f2937; }
                h1 { text-align: center; margin-bottom: 40px; color: #111827; }
                .email-container { max-width: 800px; margin: 0 auto; }
                .email-card { background: white; margin-bottom: 60px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); }
                .email-meta { background: #1f2937; color: white; padding: 20px; }
                .email-body { padding: 0; background: #ffffff; }
                .email-body-inner { padding: 40px; }
                h2 { margin: 0 0 8px 0; font-size: 18px; font-weight: 600; color: #f9fafb; }
                .meta-row { font-size: 14px; opacity: 0.8; font-family: monospace; }
                .preview-label { display: inline-block; background: #4b5563; padding: 4px 8px; border-radius: 4px; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; font-weight: 600; }
            </style>
        </head>
        <body>
            <h1>Employee Suite Transactional Emails</h1>
            <div class="email-container">
        """)
        
        for i, email in enumerate(captured_emails):
            f.write(f"""
            <div class="email-card">
                <div class="email-meta">
                    <span class="preview-label">Email {i+1}</span>
                    <h2>{email['subject']}</h2>
                    <div class="meta-row">To: {email['to']}</div>
                </div>
                <div class="email-body">
                    <div class="email-body-inner">
                        {email['html']}
                    </div>
                </div>
            </div>
            """)
        
        f.write("</div></body></html>")
    
    logger.info(f"\nSUCCESS: Generated {len(captured_emails)} email previews in '{preview_path}'")

if __name__ == "__main__":
    test_emails()
