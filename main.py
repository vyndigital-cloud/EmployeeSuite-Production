#!/usr/bin/env python3
"""
Main entry point for MissionControl Shopify App.
WSGI servers should use: gunicorn main:app
"""

import os
import sys
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent.absolute()
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from app_factory import create_app

# For WSGI servers (Gunicorn, uWSGI, etc.)
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)
