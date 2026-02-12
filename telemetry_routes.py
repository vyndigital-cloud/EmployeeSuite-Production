"""
Client Telemetry Routes
Receives diagnostic data from Sentinel Bot and other client-side instrumentation
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime

telemetry_bp = Blueprint('telemetry', __name__, url_prefix='/client-telemetry')
logger = logging.getLogger(__name__)

@telemetry_bp.route('/log', methods=['POST'])
def receive_client_log():
    """
    Receives telemetry data from Sentinel Bot
    Logs forensic information about App Bridge initialization
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_id = data.get('user_id', 'UNKNOWN')
        events = data.get('events', [])
        environment = data.get('environment', {})
        total_elapsed = data.get('total_elapsed_ms', 0)
        
        # Log summary
        logger.info(
            f"🤖 SENTINEL REPORT | "
            f"User: {user_id} | "
            f"Events: {len(events)} | "
            f"Total Time: {total_elapsed}ms | "
            f"URL: {environment.get('url', 'unknown')}"
        )
        
        # Log each event with details
        for event in events:
            timestamp = event.get('timestamp', 'unknown')
            elapsed = event.get('elapsed_ms', 0)
            message = event.get('message', '')
            
            # Extract relevant data fields (excluding timestamp/elapsed/message)
            data_fields = {k: v for k, v in event.items() 
                          if k not in ['timestamp', 'elapsed_ms', 'message']}
            
            log_line = f"🤖 [{elapsed}ms] {message}"
            if data_fields:
                log_line += f" | {data_fields}"
            
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
