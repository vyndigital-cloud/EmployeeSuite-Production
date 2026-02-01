"""
Shopify Session Token Verification for Embedded Apps
MANDATORY requirement as of January 2025
"""

import os
from functools import wraps

import jwt
from flask import jsonify, request

from logging_config import logger

SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")


def validate_shopify_config():
    """Validate Shopify configuration on module load"""
    api_key = os.getenv("SHOPIFY_API_KEY", "").strip()
    api_secret = os.getenv("SHOPIFY_API_SECRET", "").strip()

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
        # Check if this is an embedded app request
        auth_header = request.headers.get("Authorization")
        has_session_token = auth_header and auth_header.startswith("Bearer ")

        # If session token is present, verify it (embedded app)
        if has_session_token:
            token = auth_header.split(" ")[1] if " " in auth_header else None
            if not token:
                return jsonify({"error": "Invalid token format"}), 401

            try:
                # Decode and verify the JWT token
                # Shopify signs session tokens with SHOPIFY_API_SECRET
                payload = jwt.decode(
                    token,
                    SHOPIFY_API_SECRET,
                    algorithms=["HS256"],
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_iat": True,
                        "verify_aud": False,  # We verify audience manually below
                        "require": ["iss", "dest", "aud", "sub", "exp", "nbf", "iat"],
                    },
                )

                logger.debug(
                    f"JWT payload decoded successfully: {list(payload.keys())}"
                )

                # Verify audience (should be API key)
                aud = payload.get("aud")

                # LAZY LOAD: Get API key at runtime with better error handling
                current_api_key = os.getenv("SHOPIFY_API_KEY", "").strip()

                # Remove quotes if present (common environment variable issue)
                if current_api_key and len(current_api_key) > 2:
                    if (
                        current_api_key.startswith('"')
                        and current_api_key.endswith('"')
                    ) or (
                        current_api_key.startswith("'")
                        and current_api_key.endswith("'")
                    ):
                        current_api_key = current_api_key[1:-1].strip()

                # Validate API key is present
                if not current_api_key:
                    logger.error(
                        "SHOPIFY_API_KEY environment variable is NOT SET or empty"
                    )
                    return jsonify(
                        {"error": "Server configuration error - missing API key"}
                    ), 500

                # Enhanced logging for debugging
                logger.debug(f"JWT audience validation:")
                logger.debug(f"  Token audience: {aud}")
                logger.debug(
                    f"  Expected API key: {current_api_key[:8]}{'*' * (len(current_api_key) - 8)}"
                )
                logger.debug(f"  Audience length: {len(aud) if aud else 0}")
                logger.debug(f"  API key length: {len(current_api_key)}")

                # Validate audience matches API key
                if not aud:
                    logger.warning("JWT token missing audience field")
                    return jsonify({"error": "Invalid token - missing audience"}), 401

                if aud != current_api_key:
                    logger.warning(f"JWT audience mismatch:")
                    logger.warning(
                        f"  Received: {aud[:8]}{'*' * max(0, len(aud) - 8)} (len: {len(aud)})"
                    )
                    logger.warning(
                        f"  Expected: {current_api_key[:8]}{'*' * max(0, len(current_api_key) - 8)} (len: {len(current_api_key)})"
                    )

                    # Check for common issues
                    if aud.strip() == current_api_key.strip():
                        logger.warning(
                            "Audience matches after stripping whitespace - check environment variable"
                        )
                    elif aud.lower() == current_api_key.lower():
                        logger.warning(
                            "Audience matches case-insensitive - check case sensitivity"
                        )

                    return jsonify(
                        {"error": "Invalid token audience (API Key mismatch)"}
                    ), 401

                # Verify destination (should match shop domain)
                dest = payload.get("dest", "")
                if not dest or not dest.endswith(".myshopify.com"):
                    logger.warning(f"Invalid destination in session token: {dest}")
                    return jsonify({"error": "Invalid token destination"}), 401

                request.shop_domain = dest.replace("https://", "").split("/")[0]
                request.session_token_verified = True

                logger.debug(f"Session token verified for shop: {request.shop_domain}")

                # Auto-login user for embedded app
                try:
                    from flask_login import login_user

                    from models import ShopifyStore, User

                    # Find store by domain
                    store = ShopifyStore.query.filter_by(
                        shop_url=request.shop_domain, is_active=True
                    ).first()
                    if store and store.user_id:
                        user = User.query.get(store.user_id)
                        if user and user.has_access():
                            login_user(user)
                            logger.debug(
                                f"Auto-logged in user {user.id} for shop {request.shop_domain}"
                            )
                except Exception as e:
                    logger.error(f"Error auto-logging in user: {e}")

            except jwt.ExpiredSignatureError:
                logger.warning("JWT session token has expired")
                return jsonify(
                    {"error": "Session token has expired - please refresh the page"}
                ), 401

            except jwt.InvalidSignatureError:
                logger.warning("JWT session token has invalid signature")
                # Check if API secret is correct
                api_secret = os.getenv("SHOPIFY_API_SECRET", "").strip()
                if not api_secret:
                    logger.error(
                        "SHOPIFY_API_SECRET is missing - cannot verify JWT signature"
                    )
                    return jsonify(
                        {"error": "Server configuration error - missing API secret"}
                    ), 500
                return jsonify({"error": "Invalid session token signature"}), 401

            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid JWT session token: {e}")

                # Try to decode without verification for debugging
                try:
                    debug_payload = jwt.decode(
                        token, options={"verify_signature": False}
                    )
                    debug_aud = debug_payload.get("aud", "MISSING")
                    debug_iss = debug_payload.get("iss", "MISSING")
                    logger.warning(f"DEBUG - Token contents:")
                    logger.warning(f"  Audience: {debug_aud}")
                    logger.warning(f"  Issuer: {debug_iss}")
                    logger.warning(
                        f"  Expected API Key: {SHOPIFY_API_KEY[:8] + '****' if SHOPIFY_API_KEY else 'NOT_SET'}"
                    )
                except Exception:
                    logger.warning("Could not decode token for debugging")

                return jsonify({"error": "Invalid session token format"}), 401

            except Exception as e:
                logger.error(
                    f"Unexpected error verifying session token: {e}", exc_info=True
                )
                return jsonify({"error": "Session token verification failed"}), 401

        # If no session token, route will continue to Flask-Login check (if @login_required is used)
        # This allows non-embedded access to still work
        return f(*args, **kwargs)

    return decorated_function


# Removed _is_embedded_app_request - now handled inline in verify_session_token decorator


def get_shop_from_session_token():
    """
    Extract shop domain from verified session token
    Should only be called after verify_session_token decorator
    """
    return getattr(request, "shop_domain", None)
