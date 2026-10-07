"""
Configuration management for Verve application.

This module provides environment-specific configuration classes
for development, testing, and production environments.
"""

import os
from datetime import timedelta
from pathlib import Path
from sqlalchemy.pool import NullPool


class Config:
    """Base configuration class with default settings."""
    
    # Base directory of the application
    BASE_DIR = Path(__file__).parent.absolute()
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('SQLALCHEMY_DATABASE_URI')
        or os.environ.get('DATABASE_URL')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_REFRESH_EACH_REQUEST = False
    WTF_CSRF_TIME_LIMIT = 2 * 60 * 60

    # Managed Neon Auth URL for the same database branch.
    NEON_AUTH_BASE_URL = os.environ.get('NEON_AUTH_BASE_URL', '')
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file size
    UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
    
    # Logging
    # Vercel has a read-only filesystem, so we disable file logging there
    LOG_FILE = None if os.environ.get('VERCEL') else BASE_DIR / "verve.log"
    LOG_LEVEL = "INFO"

    
    
    @staticmethod
    def init_app(app):
        """Initialize application with this configuration."""
    # Flask settings


class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    DEBUG = False
    TESTING = False
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """Production environment configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Secure cookies in production (HTTPS)
    SESSION_COOKIE_SECURE = True
    
    # SQLAlchemy engine options for serverless Postgres providers such as Neon.
    # NullPool ensures that connections are not kept open between requests,
    # which avoids leaking connections across serverless invocations.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": NullPool,
        "pool_pre_ping": True,
    }

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
