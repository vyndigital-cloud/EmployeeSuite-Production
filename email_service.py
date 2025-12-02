import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_welcome_email(user_email):
    """Send welcome email when user signs up"""
    message = Mail(
        from_email='noreply@employeesuite.app',
        to_emails=user_email,
        subject='Welcome to Employee Suite - Your Trial Has Started',
        html_content=f'''
        <div style="font-family: Inter, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #171717;">Welcome to Employee Suite!</h1>
            <p style="font-size: 16px; color: #525252; line-height: 1.6;">Your 2-day free trial has started.</p>
            
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
        '''
    )
    
    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        sg.send(message)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_trial_expiry_warning(user_email, days_left):
    """Send email 1 day before trial expires"""
    message = Mail(
        from_email='noreply@employeesuite.app',
        to_emails=user_email,
        subject=f'Your Employee Suite Trial Ends in {days_left} Day{"s" if days_left != 1 else ""}',
        html_content=f'''
        <div style="font-family: Inter, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #171717;">Your Trial Ends Soon</h1>
            <p style="font-size: 16px; color: #525252; line-height: 1.6;">
                You have {days_left} day{"s" if days_left != 1 else ""} left in your free trial.
            </p>
            
            <div style="background: #fffbeb; border-left: 4px solid #f59e0b; padding: 20px; margin: 20px 0;">
                <p style="color: #92400e; font-weight: 600;">Don't lose access to:</p>
                <ul style="color: #92400e;">
                    <li>Real-time inventory tracking</li>
                    <li>Low-stock alerts</li>
                    <li>Revenue reports</li>
                </ul>
            </div>
            
            <a href="https://employeesuite-production.onrender.com/subscribe" 
               style="display: inline-block; background: #171717; color: white; padding: 14px 28px; 
                      text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: 600;">
                Subscribe Now - $500/month
            </a>
            
            <p style="font-size: 13px; color: #737373; margin-top: 30px;">
                $1,000 setup fee + $500/month after trial
            </p>
        </div>
        '''
    )
    
    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        sg.send(message)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_payment_success(user_email):
    """Send email when payment succeeds"""
    message = Mail(
        from_email='noreply@employeesuite.app',
        to_emails=user_email,
        subject='Payment Confirmed - Welcome to Employee Suite Pro',
        html_content='''
        <div style="font-family: Inter, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #16a34a;">✓ Payment Confirmed</h1>
            <p style="font-size: 16px; color: #525252;">Your subscription is now active.</p>
            
            <div style="background: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="color: #166534; font-weight: 600;">You now have unlimited access to:</p>
                <ul style="color: #166534;">
                    <li>Real-time inventory tracking</li>
                    <li>Automated low-stock alerts</li>
                    <li>Revenue analytics & reports</li>
                    <li>Priority support</li>
                </ul>
            </div>
            
            <a href="https://employeesuite-production.onrender.com/dashboard" 
               style="display: inline-block; background: #171717; color: white; padding: 12px 24px; 
                      text-decoration: none; border-radius: 6px; margin: 20px 0;">
                Go to Dashboard
            </a>
        </div>
        '''
    )
    
    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        sg.send(message)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_payment_failed(user_email):
    """Send email when payment fails"""
    message = Mail(
        from_email='noreply@employeesuite.app',
        to_emails=user_email,
        subject='Payment Failed - Update Your Payment Method',
        html_content='''
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
        '''
    )
    
    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        sg.send(message)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False
