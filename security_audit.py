"""
Security Audit Mode - Fail-Loud-But-Don't-Crash
Logs all security and data discrepancies without breaking production
Enable with: AUDIT_MODE=strict in environment variables
"""
import os
import logging
from datetime import datetime
from collections import defaultdict
from flask import request, session, g

# Audit logger
audit_logger = logging.getLogger('security_audit')
audit_logger.setLevel(logging.WARNING)

# Track discrepancy patterns (in-memory for speed)
discrepancy_stats = defaultdict(int)

# Audit mode configuration
AUDIT_MODE = os.getenv("AUDIT_MODE", "off")  # off, log, strict
AUDIT_STRICT = (AUDIT_MODE == "strict")  # True = raise exceptions (DEV ONLY!)

# Routes that are expected to have no JWT/shop (whitelist)
EXPECTED_NO_AUTH = {
    '/health', '/ready', '/_ah/health',  # Health checks
    '/static', '/favicon.ico',            # Static assets
    '/privacy', '/terms', '/legal',       # Legal pages  
    '/oauth/install', '/oauth/callback',  # OAuth flow (gets JWT later)
    '/webhooks',                          # Shopify webhooks (HMAC auth)
}

def is_whitelisted_route(endpoint):
    """Check both blueprinted endpoint names and raw paths"""
    if not request:
        return False
    
    path = request.path
    
    # Whitelisted endpoint suffixes (blueprint-agnostic)
    WHITELISTED_SUFFIXES = {
        'static', 'health', 'ready', 'webhooks',
        'privacy', 'terms', 'legal', 'favicon',
        'dashboard', 'home',  # Trusted user-facing routes
    }
    
    # Check 1: Endpoint suffix match (catches any blueprint.suffix)
    if endpoint:
        for suffix in WHITELISTED_SUFFIXES:
            if endpoint == suffix or endpoint.endswith(f'.{suffix}'):
                return True
    
    # Check 2: Path prefix match
    return any(path.startswith(p) for p in EXPECTED_NO_AUTH)


def audit_security_discrepancies(details):
    """
    Audit security discrepancies - LOGS but doesn't crash
    
    Args:
        details: Dict with keys: url, endpoint, environment, 
                is_jwt_verified, shop_domain, user_id
    """
    if not request:
        return
    
    # === FAST-TRACK BYPASS: Health Checks & System Monitors ===
    # Skip heavy audit logic for Render health checks (eliminate 500ms latency)
    user_agent = request.headers.get('User-Agent', '')
    if request.path in ('/health', '/ready', '/_ah/health') or 'Render' in user_agent:
        return  # Bypass audit entirely for system heartbeats
    
    endpoint = details.get('endpoint', '')
    url = details.get('url', '')
    
    # Skip whitelisted routes
    if is_whitelisted_route(endpoint):
        return
    
    # === DISCREPANCY 1: Unverified JWT (IMMEDIATE ALERT) ===
    # ABSOLUTE VISIBILITY: Alert on ANY unverified JWT access (not just production)
    if not details.get('is_jwt_verified'):
        if not is_whitelisted_route(endpoint):
            discrepancy_stats['unverified_jwt'] += 1
            
            # CRITICAL ALERT: Unverified JWT access detected
            msg = (
                f"🚨 CRITICAL ALERT: Unverified JWT Access | "
                f"Endpoint: {endpoint} | "
                f"URL: {url} | "
                f"Shop: {details.get('shop_domain', 'MISSING')} | "
                f"User: {details.get('user_id', 'NONE')} | "
                f"Environment: {details.get('environment', 'UNKNOWN')} | "
                f"Method: {details.get('method', 'UNKNOWN')} | "
                f"IP: {details.get('ip', 'UNKNOWN')} | "
                f"User-Agent: {details.get('user_agent', 'NONE')}"
            )
            
            # Log as ERROR for immediate visibility (not just warning)
            audit_logger.error(msg)
            
            # STRICT MODE: Crash (DEV ONLY!)
            if AUDIT_STRICT:
                raise PermissionError(msg)
    
    # === DISCREPANCY 2: Missing Shop Domain ===
    shop = details.get('shop_domain')
    if not shop or shop == 'None':
        if not is_whitelisted_route(endpoint):
            discrepancy_stats['missing_shop'] += 1
            
            msg = (
                f"⚠️  DATA DISCREPANCY: Missing shop_domain | "
                f"Endpoint: {endpoint} | "
                f"User: {details.get('user_id', 'NONE')} | "
                f"JWT Verified: {details.get('is_jwt_verified', False)} | "
                f"URL: {url}"
            )
            
            audit_logger.warning(msg)
            
            # STRICT MODE: Crash (DEV ONLY!)
            if AUDIT_STRICT:
                raise ValueError(msg)
    
    # === DISCREPANCY 3: Session/Cookie Login in Stateless Context ===
    if details.get('is_jwt_verified') is False and details.get('user_id'):
        # User is logged in via cookie but JWT verification failed
        discrepancy_stats['cookie_login_without_jwt'] += 1
        
        msg = (
            f"🔐 AUTH DISCREPANCY: Cookie-based login without JWT | "
            f"Endpoint: {endpoint} | "
            f"User: {details.get('user_id')} | "
            f"Shop: {details.get('shop_domain', 'NONE')}"
        )
        
        audit_logger.info(msg)  # INFO, not WARNING (this is expected fallback)


def get_audit_report():
    """Get current audit statistics"""
    total_discrepancies = sum(discrepancy_stats.values())
    
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'audit_mode': AUDIT_MODE,
        'total_discrepancies': total_discrepancies,
        'breakdown': dict(discrepancy_stats),
        'top_issues': sorted(
            discrepancy_stats.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
    }


def clear_audit_stats():
    """Clear audit statistics (call daily)"""
    discrepancy_stats.clear()
