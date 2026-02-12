"""
Telemetry Routes - Client-Side Diagnostic Reporting
Receives forensic data from Sentinel Bot and other client-side monitors
"""

from flask import Blueprint, request, jsonify
import logging
import json
from datetime import datetime

telemetry_bp = Blueprint('telemetry', __name__, url_prefix='/telemetry')

# Dedicated logger for telemetry
telemetry_logger = logging.getLogger('telemetry')
telemetry_logger.setLevel(logging.INFO)


@telemetry_bp.route('/log', methods=['POST'])
def client_telemetry_log():
    """
    Receives diagnostic logs from Sentinel Bot
    Used for forensic analysis of App Bridge failures
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_id = data.get('user_id', 'UNKNOWN')
        timestamp = data.get('timestamp', datetime.utcnow().isoformat())
        level = data.get('level', 'INFO')
        
        # Log the telemetry report
        telemetry_logger.info(f"🤖 SENTINEL REPORT | User: {user_id} | Level: {level}")
        
        # Log events if provided
        events = data.get('events', [])
            logger.info(log_line)
        
        # Log critical failures
        critical_events = [e for e in events if 'CRITICAL' in e.get('message', '')]
        if critical_events:
            logger.error(
                f"🚨 SENTINEL DETECTED {len(critical_events)} CRITICAL ISSUE(S) | "
                f"User: {user_id}"
            )
            for event in critical_events:
                logger.error(f"   → {event.get('message', 'Unknown issue')}")
        
        return jsonify({
            'status': 'received',
            'events_logged': len(events),
            'user_id': user_id
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Failed to process Sentinel report: {e}")
        return jsonify({'error': 'Failed to process telemetry data'}), 500


@telemetry_bp.route('/ping', methods=['GET'])
def telemetry_ping():
    """Health check for telemetry endpoint"""
    return jsonify({
        'status': 'ok',
        'endpoint': 'client-telemetry',
        'timestamp': datetime.utcnow().isoformat()
    }), 200
