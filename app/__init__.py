"""
Verve - Vocabulary Learning Application.

This package provides a Flask-based spaced repetition system
for learning vocabulary efficiently.
"""

import logging
from pathlib import Path
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

from config import config


def create_app(config_name: str = 'default') -> Flask:
    """
    Application factory for creating Flask app instances.
    
    This pattern allows for easier testing and multiple app instances
    with different configurations.
    
    Args:
        config_name: Name of the configuration to use ('development', 'production', 'testing')
        
    Returns:
        Configured Flask application instance
    """
    # Get the base directory (project root) - one level up from app package
    import os
    base_dir = Path(__file__).parent.parent.absolute()
    
    # Create Flask app with correct template and static folder paths
    app = Flask(__name__,
                template_folder=str(base_dir / 'templates'),
                static_folder=str(base_dir / 'static'))
    
    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Setup logging
    setup_logging(app)
    
    # Initialize database
    from app.database import init_db
    init_db(app)
    
    # Initialize Flask-Login
    setup_login_manager(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Log startup
    app.logger.info(f"Verve application started with {config_name} configuration")
    
    return app



def setup_logging(app: Flask) -> None:
    """
    Configure application logging.
    
    Args:
        app: Flask application instance
    """
    # Create logs directory if it doesn't exist
    log_file = app.config.get('LOG_FILE')
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(exist_ok=True)
        
        # Configure file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        app.logger.addHandler(file_handler)
    
    # Set log level
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    app.logger.setLevel(getattr(logging, log_level))


def setup_login_manager(app: Flask) -> None:
    """
    Configure Flask-Login.
    
    Args:
        app: Flask application instance
    """
    from flask_login import LoginManager
    from app.models import User
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Bitte melden Sie sich an, um auf diese Seite zuzugreifen.'
    login_manager.login_message_category = 'error'

    
    @login_manager.user_loader
    def load_user(user_id):
        from app.services import UserService
        return UserService.get_user_by_id(str(user_id))


def register_blueprints(app: Flask) -> None:
    """
    Register Flask blueprints.
    
    Args:
        app: Flask application instance
    """
    from app.routes import main_bp, api_bp, auth_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)


def register_error_handlers(app: Flask) -> None:
    """
    Register error handlers for the application.
    
    Args:
        app: Flask application instance
    """
    from flask import render_template, jsonify, request
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        # Return JSON for API requests
        if request.path.startswith('/api/'):
            return jsonify({
                'status': 'error',
                'message': 'Resource not found'
            }), 404
        
        # Return HTML for regular requests
        from app.services import VocabService
        from flask_login import current_user
        
        sets = []
        if current_user.is_authenticated:
            sets = VocabService.get_all_set_names(current_user.id)
            
        sidebar_collapsed = request.cookies.get('sidebar_collapsed', 'false') == 'true'
        
        return render_template(
            'base.html',
            sets=sets,
            sidebar_collapsed=sidebar_collapsed
        ), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        app.logger.error(f"Internal server error: {error}")
        
        # Return JSON for API requests
        if request.path.startswith('/api/'):
            return jsonify({
                'status': 'error',
                'message': 'Internal server error'
            }), 500
        
        # Return HTML for regular requests
        from app.services import VocabService
        from flask_login import current_user
        
        sets = []
        if current_user.is_authenticated:
            sets = VocabService.get_all_set_names(current_user.id)
            
        sidebar_collapsed = request.cookies.get('sidebar_collapsed', 'false') == 'true'
        
        return render_template(
            'base.html',
            sets=sets,
            sidebar_collapsed=sidebar_collapsed,
            error_message=str(error)
        ), 500


__version__ = '2.0.0'
