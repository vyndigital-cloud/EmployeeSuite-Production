"""
Shopify Session Token Verification for Embedded Apps
MANDATORY requirement as of January 2025
"""

import os
from functools import wraps

import jwt
from flask import jsonify, request
from flask_login import current_user

# Replace the import at the top:
try:
    from logging_config import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


def normalize_api_key(api_key):
    """Normalize API key by removing surrounding quotes if present"""
    if not api_key:
        return api_key

    # Convert to string and strip whitespace
    api_key = str(api_key).strip()

    # Remove surrounding quotes (single or double) - but only if they wrap the entire string
    if len(api_key) >= 2:
        if (api_key.startswith('"') and api_key.endswith('"')) or (
            api_key.startswith("'") and api_key.endswith("'")
        ):
            api_key = api_key[1:-1].strip()

    return api_key


def get_normalized_api_key():
    """Get normalized API key - called when needed to avoid startup issues"""
    return normalize_api_key(os.getenv("SHOPIFY_API_KEY", ""))


def get_api_secret():
    """Get API secret - called when needed"""
    return os.getenv("SHOPIFY_API_SECRET", "").strip()


def validate_shopify_config():
    """Validate Shopify configuration on module load"""
    api_key = get_normalized_api_key()
    api_secret = get_api_secret()

    issues = []

    if not api_key:
        issues.append("SHOPIFY_API_KEY is missing")
    elif len(api_key) < 20:
        issues.append(f"SHOPIFY_API_KEY seems too short ({len(api_key)} chars)")

    if not api_secret:
        issues.append("SHOPIFY_API_SECRET is missing")
    elif len(api_secret) < 30:
        issues.append(f"SHOPIFY_API_SECRET seems too short ({len(api_secret)} chars)")

    if api_key and api_secret and api_key == api_secret:
        issues.append(
            "SHOPIFY_API_KEY and SHOPIFY_API_SECRET are the same (they should be different)"
        )

    if issues:
        logger.error("Shopify configuration issues found:")
        for issue in issues:
            logger.error(f"  - {issue}")
        logger.error(
            "Check your Render environment variables against your Shopify Partners Dashboard"
        )
    else:
        logger.info("✅ Shopify configuration validated successfully")


# Validate configuration on module load
validate_shopify_config()


def verify_session_token(f):
    """
    Decorator to verify Shopify session token for embedded app requests
    MANDATORY for embedded apps as of January 2025

    For embedded apps: Verifies session token from Authorization header
    For non-embedded: Falls back to Flask-Login (if @login_required is also used)
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Check for JWT (Authorization header OR query param 'id_token')
        auth_header = request.headers.get("Authorization")
        id_token_param = request.args.get("id_token")
        
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1] if " " in auth_header else None
        elif id_token_param:
            token = id_token_param

        if token:

            try:
                # [DECODE LOGIC REMAINS - Verify signature/exp/iat/aud/dest]
                api_secret = get_api_secret()
                current_api_key = get_normalized_api_key()
                
                payload = jwt.decode(
                    token,
                    api_secret,
                    algorithms=["HS256"],
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_iat": True,
                        "require": ["iss", "dest", "aud", "sub", "exp", "nbf", "iat"],
                    },
                    audience=current_api_key
                )

                # Verify destination
                dest = payload.get("dest", "")
                if not dest or not dest.endswith(".myshopify.com"):
                    logger.warning(f"Invalid JWT destination: {dest}")
                    return jsonify({"error": "Invalid session token destination"}), 401

                request.shop_domain = dest.replace("https://", "").split("/")[0]
                request.session_token_verified = True
                
                logger.debug(f"JWT Verified for {request.shop_domain}")

            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Session token expired", "action": "refresh"}), 401
            except Exception as e:
                logger.warning(f"JWT Validation failed: {e}")
                return jsonify({"error": "Invalid session token", "action": "refresh"}), 401

        # 2. STRICT MODE: If we are in an iframe (embedded), we MUST HAVE a verified JWT
        # We detect embeddedness by checking for the 'embedded' or 'shop' param in the URL
        # or the presence of the Sec-Fetch-Dest: iframe header
        is_embedded_context = (
            request.args.get("embedded") == "1" or 
            request.headers.get("Sec-Fetch-Dest") == "iframe" or
            (request.args.get("shop") and not current_user.is_authenticated)
        )

        if is_embedded_context and not getattr(request, 'session_token_verified', False):
            # If we are supposedly embedded but have no verified JWT, this is a "Ghost" or Spoof attempt
            logger.warning(f"Blocked unverified embedded request to {request.path}")
            return jsonify({"error": "Verified Session Token Required", "action": "refresh"}), 403

        return f(*args, **kwargs)
        return f(*args, **kwargs)

    return decorated_function


# Removed _is_embedded_app_request - now handled inline in verify_session_token decorator


def get_bearer_token():
    """Extract Bearer token from Authorization header"""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1] if " " in auth_header else None
    return None


def get_shop_from_session_token():
    """
    Extract shop domain from verified session token
    Should only be called after verify_session_token decorator
    """
    return getattr(request, "shop_domain", None)


def verify_session_token_stateless(token):
    """
    Verify a Shopify session token without altering request state (stateless).
    Used by middleware for global identity extraction.
    """
    if not token:
        logger.debug("Stateless JWT: No token provided")
        return None

    try:
        api_secret = get_api_secret()
        current_api_key = get_normalized_api_key()

        if not api_secret or not current_api_key:
            logger.error("Stateless JWT: Missing SHOPIFY_API_SECRET or SHOPIFY_API_KEY")
            return None

        payload = jwt.decode(
            token,
            api_secret,
            algorithms=["HS256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "require": ["iss", "dest", "aud", "sub", "exp", "nbf", "iat"],
            },
            audience=current_api_key
        )
        logger.debug(f"Stateless JWT: Verified for {payload.get('dest')}")
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Stateless JWT: Token expired")
        return None
    except jwt.InvalidSignatureError:
        logger.error("Stateless JWT: Invalid signature (Check SHOPIFY_API_SECRET)")
        return None
    except jwt.InvalidAudienceError:
        logger.error(f"Stateless JWT: Invalid audience (Check SHOPIFY_API_KEY matches aud in token)")
        return None
    except Exception as e:
        logger.warning(f"Stateless JWT: Verification failed: {e}")
        return None
