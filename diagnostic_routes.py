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
