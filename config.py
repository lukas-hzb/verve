"""
Configuration management for Verve application.

This module provides environment-specific configuration classes
for development, testing, and production environments.
"""

import os
from pathlib import Path


class Config:
    """Base configuration class with default settings."""
    
    # Base directory of the application
    BASE_DIR = Path(__file__).parent.absolute()
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{BASE_DIR / "verve.db"}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = 365 * 24 * 60 * 60  # 1 year in seconds
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file size
    UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
    
    # Logging
    LOG_FILE = BASE_DIR / "verve.log"
    LOG_LEVEL = "INFO"
    
    @staticmethod
    def init_app(app):
        """Initialize application with this configuration."""
    # Flask settings


class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    DEBUG = True
    TESTING = False
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """Production environment configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Secure cookies in production (HTTPS)
    SESSION_COOKIE_SECURE = True
    
    # In production, SECRET_KEY must be set via environment variable
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Ensure secret key is set in production
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY environment variable must be set in production")


class TestingConfig(Config):
    """Testing environment configuration."""
    
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
    
    # Use in-memory database for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    



# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
