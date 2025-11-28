import os
from app import create_app


# Determine configuration from environment variable
config_name = os.getenv('FLASK_CONFIG', 'production')

# Create application instance
app = create_app(config_name)