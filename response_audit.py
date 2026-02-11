"""
Response Audit - After-Request Hook
Catches performance and response-level discrepancies
Works in tandem with security_audit.py (request-level checks)
"""
import os
import time
from flask import request, g
from collections import defaultdict

# Performance thresholds
LATENCY_THRESHOLD_MS = 500  # Flag responses slower than 500ms
LATENCY_THRESHOLD_CRITICAL_MS = 2000  # Critical if slower than 2s

# Stats tracking
response_stats = defaultdict(int)

AUDIT_MODE = os.getenv("AUDIT_MODE", "off")

def audit_response_discrepancies(response):
    """
    After-request hook to audit response-level discrepancies
    
    Checks:
    1. Unverified JWT but 200 OK (security gap)
    2. High latency (performance issue)
    3. Status code mismatches
    """
    if AUDIT_MODE == "off":
        return response
    
    status = "CLEAN"
    issues = []
    
    # Skip static files and health checks
    if request.endpoint in ('static', None) or request.path.startswith(('/static', '/health', '/_ah')):
        return response
    
    # === Check 1: JWT Verification Status ===
    # If request was NOT JWT verified but returned 200, that's a potential security gap
    is_jwt_verified = getattr(request, 'session_token_verified', None)
    
    # Only flag if:
    # 1. We expected JWT verification (production + embedded context)
    # 2. JWT was NOT verified
    # 3. Response was successful (200)
    if response.status_code == 200:
        if is_jwt_verified is False:  # Explicitly False (not None)
            # Check if this route SHOULD have JWT
            shop = getattr(request, 'shop_domain', None)
            embedded = request.headers.get('Sec-Fetch-Dest') == 'iframe' or request.args.get('embedded') == '1'
            
            if embedded and shop:
                issues.append("UNVERIFIED_JWT_SUCCESS")
                status = "SECURITY_DISCREPANCY"
                response_stats['unverified_jwt_200'] += 1
    
    # === Check 2: High Latency ===
    # Check if request took too long
    if hasattr(g, 'request_start_time'):
        duration_ms = (time.time() - g.request_start_time) * 1000
        
        if duration_ms > LATENCY_THRESHOLD_CRITICAL_MS:
            issues.append(f"CRITICAL_LATENCY_{int(duration_ms)}ms")
            status = "PERFORMANCE_CRITICAL"
            response_stats['critical_latency'] += 1
        elif duration_ms > LATENCY_THRESHOLD_MS:
            issues.append(f"HIGH_LATENCY_{int(duration_ms)}ms")
            status = "PERFORMANCE_GAP"
            response_stats['high_latency'] += 1
        
        # Add X-Response-Time header for debugging
        response.headers['X-Response-Time'] = f"{duration_ms:.2f}ms"
    
    # === Check 3: Status Code Anomalies ===
    # 403 on routes that should be accessible
    if response.status_code == 403:
        if request.endpoint not in ('admin', 'settings'):  # Expected protected routes
            issues.append("UNEXPECTED_403")
            status = "ACCESS_DISCREPANCY"
            response_stats['unexpected_403'] += 1
    
    # 500 errors (always log these)
    if response.status_code >= 500:
        issues.append(f"SERVER_ERROR_{response.status_code}")
        status = "ERROR"
        response_stats['server_errors'] += 1
    
    # === Logging ===
    if status != "CLEAN":
        # Emoji flag for easy searching in logs
        print(
            f"🚨 {status} | "
            f"Path: {request.path} | "
            f"Status: {response.status_code} | "
            f"Issues: {', '.join(issues)} | "
            f"Shop: {getattr(request, 'shop_domain', 'NONE')} | "
            f"JWT: {is_jwt_verified}"
        )
    
    # Add audit status to response headers (dev mode only)
    if AUDIT_MODE == "strict" and status != "CLEAN":
        response.headers['X-Audit-Status'] = status
        response.headers['X-Audit-Issues'] = ', '.join(issues)
    
    return response


def get_response_audit_stats():
    """Get response audit statistics"""
    return {
        'total_issues': sum(response_stats.values()),
        'breakdown': dict(response_stats),
        'top_issues': sorted(
            response_stats.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
    }
