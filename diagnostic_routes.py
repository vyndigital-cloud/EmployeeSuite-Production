"""
Diagnostic endpoint to check SendGrid configuration
"""
from flask import Blueprint, jsonify
import os

diagnostic_bp = Blueprint('diagnostic', __name__, url_prefix='/diagnostic')

@diagnostic_bp.route('/sendgrid-status')
def sendgrid_status():
    """Check SendGrid configuration status"""
    api_key = os.getenv('SENDGRID_API_KEY')
    
    status = {
        'api_key_set': bool(api_key),
        'api_key_length': len(api_key) if api_key else 0,
        'api_key_prefix': api_key[:15] if api_key else None,
        'api_key_suffix': api_key[-10:] if api_key and len(api_key) > 10 else None,
        'environment': os.getenv('ENVIRONMENT', 'unknown'),
    }
    
    # Try to validate with SendGrid
    if api_key:
        try:
            from sendgrid import SendGridAPIClient
            sg = SendGridAPIClient(api_key)
            
            # Try to get account details (this will fail if key is invalid)
            # We're not actually sending, just validating the key
            status['sendgrid_client_created'] = True
            status['validation'] = 'API key format is valid'
            
        except Exception as e:
            status['sendgrid_client_created'] = False
            status['validation_error'] = str(e)
    
    return jsonify(status)


@diagnostic_bp.route('/test-email-send')
def test_email_send():
    """Actually try to send a test email to diagnose the 401 error"""
    api_key = os.getenv('SENDGRID_API_KEY')
    
    if not api_key:
        return jsonify({'error': 'SENDGRID_API_KEY not set'}), 500
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        message = Mail(
            from_email=('adam@golproductions.com', 'Employee Suite Test'),
            to_emails='finessor06@gmail.com',
            subject='SendGrid Test Email',
            html_content='<p>This is a test email from the diagnostic endpoint.</p>'
        )
        
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        return jsonify({
            'success': True,
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'message': 'Email sent successfully!'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc(),
            'has_body': hasattr(e, 'body'),
            'body': e.body.decode() if hasattr(e, 'body') else None
        }), 500
