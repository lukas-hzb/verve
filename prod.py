"""
WSGI entry point for the Verve application in production.

This script exposes the `app` object which WSGI servers like Gunicorn,
uWSGI, or PythonAnywhere's WSGI loader will look for.
"""

import os
from dotenv import load_dotenv

# Explicitly load .env file to ensure environment variables are available
# This is crucial for PythonAnywhere if variables aren't set in their dashboard
project_folder = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(project_folder, '.env'))

from app import create_app

# Force production config if not set
if not os.environ.get('FLASK_CONFIG'):
    os.environ['FLASK_CONFIG'] = 'production'

# Determine configuration from environment variable
config_name = os.getenv('FLASK_CONFIG', 'production')

# Create application instance
app = create_app(config_name)

if __name__ == "__main__":
    # If run directly, run with debug disabled
    app.run(debug=False)