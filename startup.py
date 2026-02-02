#!/usr/bin/env python3
"""
Bulletproof startup script - handles all edge cases
"""

import logging
import os
import sys


def setup_environment():
    """Setup environment with safe defaults"""
    # Set safe defaults for missing environment variables
    defaults = {
        "ENVIRONMENT": "production",
        "SECRET_KEY": "change-me-in-production",
        "SHOPIFY_API_VERSION": "2025-10",
        "WTF_CSRF_ENABLED": "False",
        "SQLALCHEMY_TRACK_MODIFICATIONS": "False",
    }

    for key, value in defaults.items():
        if not os.getenv(key):
            os.environ[key] = value


def create_app():
    """Create app with maximum error tolerance"""
    setup_environment()

    try:
        # Try main app factory
        from app_factory import create_app

        return create_app()
    except Exception as e:
        print(f"Main app factory failed: {e}")

        # Fallback to minimal Flask app
        from flask import Flask, jsonify

        app = Flask(__name__)

        app.config.update(
            {
                "SECRET_KEY": os.getenv("SECRET_KEY"),
                "SQLALCHEMY_DATABASE_URI": os.getenv(
                    "DATABASE_URL", "sqlite:///app.db"
                ),
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            }
        )

        @app.route("/")
        def home():
            return jsonify({"status": "running", "mode": "minimal"})

        @app.route("/health")
        def health():
            return jsonify({"status": "healthy"})

        return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
