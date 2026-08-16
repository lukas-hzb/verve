"""
Run script for the Verve application locally.

This is the entry point for running the Flask application in development mode.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import create_app


# Always use development config for local testing
config_name = 'development'

# Create application instance
app = create_app(config_name)


if __name__ == "__main__":
    import socket

    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', 8080))

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true" and is_port_in_use(port):
        raise SystemExit(
            f"Port {port} is already in use. Stop the existing process or choose another FLASK_PORT."
        )

    print(f"Starting Verve on http://{host}:{port}")
    app.run(host=host, port=port, debug=True)
