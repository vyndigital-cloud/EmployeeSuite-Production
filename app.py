"""
Main application entry point for gunicorn
"""

from main import app

if __name__ == "__main__":
    app.run()
