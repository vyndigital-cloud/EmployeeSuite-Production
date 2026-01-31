#!/usr/bin/env python3
"""
Main entry point for MissionControl Shopify App
Uses application factory pattern to avoid circular imports
"""

import os
import sys
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent.absolute()
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from app_factory import create_app
from config import get_config


def main():
    """Main application entry point"""
    # Get configuration
    config = get_config()

    # Create application
    app = create_app()

    # Run in development mode if DEBUG is enabled
    if config.DEBUG and not config.is_production():
        app.run(
            host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True, threaded=True
        )
    else:
        # In production, this should be run with gunicorn
        print("Production mode detected. Use gunicorn to run:")
        print(f"gunicorn -w 4 -b 0.0.0.0:{os.getenv('PORT', 5000)} main:app")
        return app


# For WSGI servers (Gunicorn, uWSGI, etc.)
app = create_app()

if __name__ == "__main__":
    main()
