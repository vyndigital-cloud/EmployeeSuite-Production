"""
Main application entry point for gunicorn
"""

# Import the app directly from main.py where it's properly configured
from main import app

if __name__ == "__main__":
    app.run(debug=False)
