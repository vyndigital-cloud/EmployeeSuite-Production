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
        if events:
            telemetry_logger.info(f"🤖 Events: {len(events)}")
            for event in events[:5]:  # Log first 5 events
                msg = event.get('message', 'No message')
                elapsed = event.get('elapsed_ms', 0)
                telemetry_logger.info(f"🤖 [{elapsed}ms] {msg}")
        
        # Log state snapshots if provided
        snapshots = data.get('state_snapshots', [])
        if snapshots:
            telemetry_logger.info(f"🤖 State Snapshots: {len(snapshots)}")
        
        # Check for critical issues
        critical_events = [e for e in events if e.get('level') == 'CRITICAL']
        if critical_events:
            telemetry_logger.error(f"🚨 SENTINEL DETECTED {len(critical_events)} CRITICAL ISSUE(S)")
            for event in critical_events:
                telemetry_logger.error(f"   → {event.get('message')}")
        
        return jsonify({
            'success': True,
            'message': 'Telemetry logged',
            'events_received': len(events),
            'snapshots_received': len(snapshots)
        }), 200
        
    except Exception as e:
        telemetry_logger.error(f"❌ Failed to process telemetry: {str(e)}")
        return jsonify({'error': str(e)}), 500


@telemetry_bp.route('/heartbeat', methods=['POST'])
def heartbeat():
    """
    💓 HYDRA HEARTBEAT - Session Health Monitor
    Receives background pulse from Silent Pulse every 4 minutes
    Logs session status and token validity
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        shop = data.get('shop', 'UNKNOWN')
        status = data.get('status', 'unknown')
        token_preview = data.get('token_preview', 'N/A')
        
        # Log the heartbeat
        telemetry_logger.info(f"💓 HYDRA HEARTBEAT | Shop: {shop} | Status: {status} | Token: {token_preview}...")
        
        # Track heartbeat health
        if status == 'verified':
            telemetry_logger.info(f"✅ Session verified for {shop}")
        else:
            telemetry_logger.warning(f"⚠️ Session issue for {shop}: {status}")
        
        return jsonify({
            'success': True,
            'message': 'Heartbeat received',
            'shop': shop,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        telemetry_logger.error(f"❌ Heartbeat failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@telemetry_bp.route('/error_recovery', methods=['POST'])
def error_recovery():
    """
    🛡️ SENTINEL RECOVERY - Resource Error Handler
    Logs failed resources (scripts, images) for diagnostic purposes
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        error_type = data.get('type', 'unknown')
        shop = data.get('shop', 'UNKNOWN')
        resource = data.get('resource', 'N/A')
        
        # Log the recovery event
        telemetry_logger.warning(f"🛡️ SENTINEL RECOVERY | Shop: {shop} | Type: {error_type} | Resource: {resource}")
        
        return jsonify({
            'success': True,
            'message': 'Error recovery logged',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        telemetry_logger.error(f"❌ Error recovery logging failed: {str(e)}")
        return jsonify({'error': str(e)}), 500
