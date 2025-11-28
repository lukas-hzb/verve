"""
Run script for the Verve application locally.

This is the entry point for running the Flask application.
"""

import os
from app import create_app


# Determine configuration from environment variable
config_name = os.getenv('FLASK_CONFIG', 'development')

# Create application instance
app = create_app(config_name)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'backup':
        with app.app_context():
            from app.services.backup_service import BackupService
            success, message = BackupService.create_backup()
            print(message)
    else:
        # Get host and port from environment or use defaults
        host = os.getenv('FLASK_HOST', '127.0.0.1')
        port = int(os.getenv('FLASK_PORT', 8080))  # Using port 8080 to avoid conflicts with macOS services
        debug = config_name == 'development'
        
        app.run(host=host, port=port, debug=debug)
