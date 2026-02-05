"""
Email service with optional SendGrid dependency
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
    if not SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set - email functionality disabled")
        SENDGRID_AVAILABLE = False
    else:
        SENDGRID_AVAILABLE = True
except ImportError:
    logger.warning("SendGrid not available - email functionality disabled")
    SENDGRID_AVAILABLE = False
    SENDGRID_API_KEY = None

# SMTP Configuration (fallback when SendGrid unavailable)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'adam@golproductions.com')

SMTP_AVAILABLE = bool(SMTP_USERNAME and SMTP_PASSWORD)

# Log email service status
if SENDGRID_AVAILABLE:
    logger.info("SendGrid email service available")
elif SMTP_AVAILABLE:
    logger.info("SMTP email service available as fallback")
else:
    logger.warning("No email service configured - emails will be logged only")


def send_smtp_email(to_email, subject, html_content):
    """Send email via SMTP as fallback"""
    if not SMTP_AVAILABLE:
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"SMTP email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"SMTP email error: {e}")
        return False


def send_welcome_email(user_email):
    """Send welcome email when user signs up"""
    if not user_email:
        logger.error("No email address provided for welcome email")
        return False
        
    html_content = f"""
    <div style="font-family: Inter, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #171717;">Welcome to Employee Suite!</h1>
        <p style="font-size: 16px; color: #525252; line-height: 1.6;">Your 7-day free trial has started.</p>

        <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h2 style="font-size: 18px; color: #171717;">Quick Start:</h2>
            <ol style="color: #525252; line-height: 1.8;">
                <li>Login to your dashboard</li>
                <li>Go to Settings → Connect your Shopify store</li>
                <li>Start automating inventory tracking</li>
            </ol>
        </div>

        <a href="https://employeesuite-production.onrender.com/dashboard"
           style="display: inline-block; background: #171717; color: white; padding: 12px 24px;
                  text-decoration: none; border-radius: 6px; margin: 20px 0;">
            Go to Dashboard
        </a>

        <p style="font-size: 14px; color: #737373; margin-top: 30px;">
            Questions? Reply to this email or visit our FAQ.
        </p>
    </div>
    """

    if not SENDGRID_AVAILABLE and not SMTP_AVAILABLE:
        logger.info(f"Email disabled - would send welcome email to {user_email}")
        return True  # Return True so signup doesn't fail

    subject = "Welcome to Employee Suite - Your Trial Has Started"

    # Try SendGrid first, then SMTP fallback
    if SENDGRID_AVAILABLE:
        try:
            message = Mail(
                from_email=("adam@golproductions.com", "Employee Suite"),
                to_emails=user_email,
                subject=subject,
                html_content=html_content,
            )
            sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
            response = sg.send(message)
            logger.info(f"SendGrid email sent to {user_email}, status: {response.status_code}")
            return True
        except Exception as e:
            logger.error(f"SendGrid email error: {e}")
            # Fall through to SMTP
    
    if SMTP_AVAILABLE:
        return send_smtp_email(user_email, subject, html_content)
    
    logger.warning(f"No email service available - welcome email not sent to {user_email}")
    return True  # Don't fail signup if email fails


def send_trial_expiry_warning(user_email, days_left):
    """Send email 1 day before trial expires"""
    if not user_email:
        logger.error("No email address provided for trial warning")
        return False
        
    if not SENDGRID_AVAILABLE and not SMTP_AVAILABLE:
        logger.info(f"Email disabled - would send trial warning to {user_email}")
        return True

    subject = f"Your Employee Suite Trial Ends in {days_left} Day{'s' if days_left != 1 else ''}"
    html_content = f"""
    <div style="font-family: Inter, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #171717;">Your Trial Ends Soon</h1>
        <p style="font-size: 16px; color: #525252; line-height: 1.6;">
            You have {days_left} day{"s" if days_left != 1 else ""} left in your free trial.
        </p>

        <div style="background: #fffbeb; border-left: 4px solid #f59e0b; padding: 20px; margin: 20px 0;">
            <p style="color: #92400e; font-weight: 600;">Don't lose access to:</p>
            <ul style="color: #92400e;">
                <li>Smart Low Stock Alerts</li>
                <li>Real-Time Inventory Dashboard</li>
                <li>Revenue Analytics & Reporting</li>
            </ul>
        </div>

        <a href="https://employeesuite-production.onrender.com/subscribe"
           style="display: inline-block; background: #171717; color: white; padding: 14px 28px;
                  text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: 600;">
            Subscribe Now - $39/month
        </a>

        <p style="font-size: 13px; color: #737373; margin-top: 30px;">
            $39/month after trial - No setup fees
        </p>
    </div>
    """

    # Try SendGrid first, then SMTP fallback
    if SENDGRID_AVAILABLE:
        try:
            message = Mail(
                from_email=("adam@golproductions.com", "Employee Suite"),
                to_emails=user_email,
                subject=subject,
                html_content=html_content,
            )
            sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
            response = sg.send(message)
            logger.info(f"Trial warning email sent to {user_email}, status: {response.status_code}")
            return True
        except Exception as e:
            logger.error(f"SendGrid email error: {e}")
            # Fall through to SMTP
    
    if SMTP_AVAILABLE:
        return send_smtp_email(user_email, subject, html_content)
    
    logger.warning(f"No email service available - trial warning not sent to {user_email}")
    return False


def send_payment_success(user_email):
    """Send email when payment succeeds"""
    if not SENDGRID_AVAILABLE:
        logger.info(f"Email disabled - would send payment success to {user_email}")
        return True

    message = Mail(
        from_email=("adam@golproductions.com", "Employee Suite"),
        to_emails=user_email,
        subject="Payment Confirmed - Welcome to Employee Suite Pro",
        html_content="""
        <div style="font-family: Inter, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #16a34a;">✓ Payment Confirmed</h1>
            <p style="font-size: 16px; color: #525252;">Your subscription is now active.</p>

            <div style="background: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="color: #166534; font-weight: 600;">You now have unlimited access to:</p>
                <ul style="color: #166534;">
                    <li>📦 Smart Low Stock Alerts</li>
                    <li>📊 Real-Time Inventory Dashboard</li>
                    <li>💰 Revenue Analytics & Reporting</li>
                    <li>📥 Unlimited CSV Exports</li>
                    <li>💬 Priority Email Support</li>
                </ul>
            </div>

            <a href="https://employeesuite-production.onrender.com/dashboard"
               style="display: inline-block; background: #171717; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 6px; margin: 20px 0;">
                Go to Dashboard
            </a>
        </div>
        """,
    )

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
        return True
    except Exception as e:
        logger.error(f"Email error: {e}")
        return False


def send_cancellation_email(user_email):
    """Send email when user cancels subscription"""
    if not SENDGRID_AVAILABLE:
        logger.info(f"Email disabled - would send cancellation email to {user_email}")
        return True

    message = Mail(
        from_email=("adam@golproductions.com", "Employee Suite"),
        to_emails=user_email,
        subject="Subscription Cancelled - Employee Suite",
        html_content="""
        <div style="font-family: Inter, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #171717;">Subscription Cancelled</h1>
            <p style="font-size: 16px; color: #525252; line-height: 1.6;">
                Your Employee Suite subscription has been cancelled.
            </p>

            <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 20px; margin: 20px 0;">
                <p style="color: #991b1b; font-weight: 600;">What happens next:</p>
                <ul style="color: #991b1b;">
                    <li>You'll retain access until the end of your current billing period</li>
                    <li>No further charges will be made</li>
                    <li>Your data will be preserved for 30 days</li>
                </ul>
            </div>

            <p style="font-size: 14px; color: #737373; margin-top: 30px;">
                Changed your mind? You can reactivate anytime by logging in and subscribing again.
            </p>

            <p style="font-size: 14px; color: #737373; margin-top: 20px;">
                We're sorry to see you go. If you have feedback, reply to this email.
            </p>
        </div>
        """,
    )

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
        return True
    except Exception as e:
        logger.error(f"Email error: {e}")
        return False


def send_password_reset_email(user_email, reset_token):
    """Send password reset email with token"""
    if not user_email or not reset_token:
        logger.error("Missing email or reset token for password reset")
        return False
        
    if not SENDGRID_AVAILABLE and not SMTP_AVAILABLE:
        logger.info(f"Email disabled - would send password reset to {user_email}")
        return True

    reset_url = f"https://employeesuite-production.onrender.com/reset-password?token={reset_token}"
    subject = "Reset Your Password - Employee Suite"
    html_content = f'''
    <div style="font-family: Inter, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #171717;">Reset Your Password</h1>
        <p style="font-size: 16px; color: #525252; line-height: 1.6;">
            You requested to reset your password. Click the button below to create a new password.
        </p>

        <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="color: #737373; font-size: 14px; margin-bottom: 10px;">This link will expire in 1 hour.</p>
        </div>

        <a href="{reset_url}"
           style="display: inline-block; background: #171717; color: white; padding: 14px 28px;
                  text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: 600;">
            Reset Password
        </a>

        <p style="font-size: 14px; color: #737373; margin-top: 30px;">
            If you didn't request this, you can safely ignore this email.
        </p>
    </div>
    '''

    # Try SendGrid first, then SMTP fallback
    if SENDGRID_AVAILABLE:
        try:
            message = Mail(
                from_email=("adam@golproductions.com", "Employee Suite"),
                to_emails=user_email,
                subject=subject,
                html_content=html_content,
            )
            sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
            response = sg.send(message)
            logger.info(f"Password reset email sent to {user_email}, status: {response.status_code}")
            return True
        except Exception as e:
            logger.error(f"SendGrid email error: {e}")
            # Fall through to SMTP
    
    if SMTP_AVAILABLE:
        return send_smtp_email(user_email, subject, html_content)
    
    logger.warning(f"No email service available - password reset not sent to {user_email}")
    return False


def send_payment_failed(user_email):
    """Send email when payment fails"""
    if not user_email:
        logger.error("No email address provided for payment failed notification")
        return False
        
    if not SENDGRID_AVAILABLE and not SMTP_AVAILABLE:
        logger.info(f"Email disabled - would send payment failed email to {user_email}")
        return True

    subject = "Payment Failed - Update Your Payment Method"
    html_content = """
    <div style="font-family: Inter, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #dc2626;">Payment Failed</h1>
        <p style="font-size: 16px; color: #525252; line-height: 1.6;">
            We couldn't process your payment. Please update your payment method to continue using Employee Suite.
        </p>

        <a href="https://employeesuite-production.onrender.com/subscribe"
           style="display: inline-block; background: #dc2626; color: white; padding: 12px 24px;
                  text-decoration: none; border-radius: 6px; margin: 20px 0;">
            Update Payment Method
        </a>

        <p style="font-size: 14px; color: #737373; margin-top: 30px;">
            Your account will be suspended if payment isn't received within 3 days.
        </p>
    </div>
    """

    # Try SendGrid first, then SMTP fallback
    if SENDGRID_AVAILABLE:
        try:
            message = Mail(
                from_email=("adam@golproductions.com", "Employee Suite"),
                to_emails=user_email,
                subject=subject,
                html_content=html_content,
            )
            sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
            response = sg.send(message)
            logger.info(f"Payment failed email sent to {user_email}, status: {response.status_code}")
            return True
        except Exception as e:
            logger.error(f"SendGrid email error: {e}")
            # Fall through to SMTP
    
    if SMTP_AVAILABLE:
        return send_smtp_email(user_email, subject, html_content)
    
    logger.warning(f"No email service available - payment failed email not sent to {user_email}")
    return False


def send_report_email(user_email, report_type, report_content):
    """Send a generated report via email"""
    if not SENDGRID_AVAILABLE:
        logger.info(f"Email disabled - would send report to {user_email}")
        return True

    message = Mail(
        from_email=("adam@golproductions.com", "Employee Suite"),
        to_emails=user_email,
        subject=f"Your {report_type.title()} Report - Employee Suite",
        html_content=f"""
        <div style="font-family: Inter, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #171717;">Your {report_type.title()} Report</h1>
            <p style="font-size: 16px; color: #525252; line-height: 1.6;">
                Here is your requested report.
            </p>

            <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e5e7eb;">
                {report_content}
            </div>

            <a href="https://employeesuite-production.onrender.com/dashboard"
               style="display: inline-block; background: #171717; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 6px; margin: 20px 0;">
                View Full Dashboard
            </a>
        </div>
        """,
    )

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
        return True
    except Exception as e:
        logger.error(f"Email error: {e}")
        return False
