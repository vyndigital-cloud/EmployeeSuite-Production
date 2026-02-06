#!/usr/bin/env python3
"""
Test SendGrid API Key
"""
import os
import sys

# Get API key from environment
api_key = os.getenv('SENDGRID_API_KEY')

if not api_key:
    print("❌ SENDGRID_API_KEY environment variable is not set")
    sys.exit(1)

print(f"✅ SENDGRID_API_KEY is set")
print(f"   Length: {len(api_key)} characters")
print(f"   Starts with: {api_key[:10]}...")
print(f"   Ends with: ...{api_key[-10:]}")

# Try to import SendGrid
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    print("✅ SendGrid library imported successfully")
except ImportError as e:
    print(f"❌ Failed to import SendGrid: {e}")
    sys.exit(1)

# Try to create a client
try:
    sg = SendGridAPIClient(api_key)
    print("✅ SendGrid client created successfully")
except Exception as e:
    print(f"❌ Failed to create SendGrid client: {e}")
    sys.exit(1)

# Try to send a test email
print("\n🧪 Testing email send...")
try:
    message = Mail(
        from_email=('adam@golproductions.com', 'Employee Suite Test'),
        to_emails='finessor06@gmail.com',
        subject='SendGrid API Test',
        html_content='<p>This is a test email to verify SendGrid is working.</p>'
    )
    
    response = sg.send(message)
    print(f"✅ Email sent successfully!")
    print(f"   Status code: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    
except Exception as e:
    print(f"❌ Failed to send email: {e}")
    print(f"   Error type: {type(e).__name__}")
    if hasattr(e, 'body'):
        print(f"   Error body: {e.body}")
    sys.exit(1)

print("\n✅ All tests passed! SendGrid is configured correctly.")
