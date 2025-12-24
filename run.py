"""
Run script for the Verve application locally.

This is the entry point for running the Flask application.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import create_app


# Determine configuration from environment variable
config_name = os.getenv('FLASK_CONFIG', 'development')

# Create application instance
app = create_app(config_name)


if __name__ == "__main__":
    import sys
    import socket
    import subprocess
    import time
    import signal
    
    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    def kill_process_on_port(port):
        try:
            # Find process ID (PID) using port
            cmd = f"lsof -t -i:{port}"
            output = subprocess.check_output(cmd, shell=True).decode().strip()
            
            if output:
                pids = output.split('\n')
                for pid in pids:
                    if pid:
                        print(f"Process {pid} is using port {port}. Killing it...")
                        os.kill(int(pid), signal.SIGKILL)
                time.sleep(1)  # Wait for processes to die
                return True
        except subprocess.CalledProcessError:
            return False
        except Exception as e:
            print(f"Error killing process: {e}")
            return False

    if len(sys.argv) > 1 and sys.argv[1] == 'backup':
        with app.app_context():
            from app.services.backup_service import BackupService
            success, message = BackupService.create_backup()
            print(message)
    else:
        # Get host and port from environment or use defaults
        host = os.getenv('FLASK_HOST', '127.0.0.1')
        port = int(os.getenv('FLASK_PORT', 8080))
        debug = config_name == 'development'
        
        # Check and clear port if needed (only in main process, not reloader)
        if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            if is_port_in_use(port):
                print(f"Port {port} is in use. Attempting to clear...")
                kill_process_on_port(port)
                
                # Double check
                if is_port_in_use(port):
                    print(f"WARNING: Port {port} is still in use. Server start might fail.")
                else:
                    print(f"Port {port} cleared successfully.")
        
        print(f"Starting Verve on http://{host}:{port}")
        try:
            app.run(host=host, port=port, debug=debug)
        except Exception as e:
            print(f"Failed to start server: {e}")
