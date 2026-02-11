"""
Client Telemetry Endpoint - Receives error reports from browser
Completes the monitoring loop by capturing client-side failures
"""
from flask import Blueprint, request, jsonify, current_app
import logging

client_telemetry_bp = Blueprint('client_telemetry', __name__)
logger = logging.getLogger(__name__)

@client_telemetry_bp.route('/log_client_error', methods=['POST'])
def log_client_error():
    """
    Receive client-side error reports (App Bridge failures, timeouts, etc.)
    This completes the observability loop: server + client visibility
    """
    try:
        data = request.get_json() or {}
        
        error_type = data.get('error', 'UNKNOWN')
        detail = data.get('detail', 'No details provided')
        url = data.get('url', 'Unknown URL')
        user_agent = data.get('agent', request.headers.get('User-Agent', 'Unknown'))
        
        # Log with forensic emoji for easy searching
        logger.warning(
            f"📱 CLIENT ERROR | "
            f"Type: {error_type} | "
            f"Detail: {detail} | "
            f"URL: {url} | "
            f"Agent: {user_agent}"
        )
        
        # Track error patterns (optional - for statistics)
        current_app.client_error_stats = getattr(current_app, 'client_error_stats', {})
        current_app.client_error_stats[error_type] = current_app.client_error_stats.get(error_type, 0) + 1
        
        return jsonify({'status': 'logged'}), 200
        
    except Exception as e:
        logger.error(f"Failed to log client error: {e}")
        return jsonify({'status': 'error'}), 500
