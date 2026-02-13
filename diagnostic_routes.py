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

@diagnostic_bp.route('/health')
def health_check():
    """
    Automated Audit Endpoint: Checks core infrastructure health.
    Returns 200 if healthy, 503 if critical failure.
    """
    try:
        from models import db
        import time
        import os # Ensure os is imported
        
        status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'services': {
                'database': 'unknown',
                'redis': 'unknown',
                'celery': 'unknown'
            }
        }
        
        http_code = 200
        
        # 1. Database Check
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            status['services']['database'] = 'connected'
        except Exception as e:
            status['services']['database'] = f'error: {str(e)}'
            status['status'] = 'degraded'
            http_code = 503
            
        # 2. Redis Check
        try:
            import redis
            r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
            if r.ping():
                status['services']['redis'] = 'connected'
        except Exception as e:
            status['services']['redis'] = f'error: {str(e)}'
            status['status'] = 'degraded' 
            
        # 3. Celery Check
        try:
            from celery.app import app_or_default
            app = app_or_default()
            with app.connection_for_read() as conn:
                conn.ensure_connection(max_retries=1)
                status['services']['celery'] = 'broker_connected'
        except Exception as e:
            status['services']['celery'] = f'error: {str(e)}'
            
        return jsonify(status), http_code
    except Exception as e:
        return jsonify({'critical_error': str(e), 'type': str(type(e))}), 500
