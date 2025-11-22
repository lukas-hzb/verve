import os
import sys
import traceback

try:
    print("Starting debug run...")
    from app import create_app
    
    # Determine configuration from environment variable
    config_name = os.getenv('FLASK_CONFIG', 'development')
    print(f"Config: {config_name}")
    
    # Create application instance
    app = create_app(config_name)
    print("App created successfully")
    
    if __name__ == "__main__":
        # Get host and port from environment or use defaults
        host = os.getenv('FLASK_HOST', '127.0.0.1')
        port = int(os.getenv('FLASK_PORT', 8080))
        debug = config_name == 'development'
        
        print(f"Running on {host}:{port} debug={debug}")
        app.run(host=host, port=port, debug=debug)
        
except Exception as e:
    with open("startup_error.log", "w") as f:
        f.write(f"Error during startup:\n")
        f.write(str(e))
        f.write("\n\nTraceback:\n")
        traceback.print_exc(file=f)
    print("Error occurred, check startup_error.log")
