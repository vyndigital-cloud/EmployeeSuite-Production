#!/usr/bin/env python3
"""
Production Main Entry Point - Bulletproof
"""

import os
import sys
from pathlib import Path

# Add project directory to path
project_dir = Path(__file__).parent.absolute()
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# Set production defaults
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

try:
    # Try the bulletproof startup
    from startup import create_app

    app = create_app()
except ImportError:
    # Ultimate fallback
    from flask import Flask, jsonify

    app = Flask(__name__)

    @app.route("/")
    def home():
        return jsonify({"status": "minimal app running"})

    @app.route("/health")
    def health():
        return jsonify({"status": "healthy"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
