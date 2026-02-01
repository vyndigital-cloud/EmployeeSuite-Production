#!/usr/bin/env python3
"""
Alternative entry point for MissionControl.
Delegates to main.py. WSGI servers can use either main:app or run:app.
"""

import os

from main import app  # noqa: F401

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)
