"""
Database initialization and configuration.

This module provides the SQLAlchemy database instance and
initialization functions for the Verve application.
"""

from flask_sqlalchemy import SQLAlchemy
from flask import Flask

# SQLAlchemy instance
db = SQLAlchemy()


def init_db(app: Flask) -> None:
    """
    Initialize the database with the Flask application.
    
    Args:
        app: Flask application instance
    """
    db.init_app(app)
    
    with app.app_context():
        # Import models to ensure they're registered with SQLAlchemy
        from app.models import User, VocabSet, Card
        
        # Create all tables
        db.create_all()
        
        # Create default shared vocabulary set if it doesn't exist
        create_default_vocab_set()


def create_default_vocab_set() -> None:
    """
    Create the default shared vocabulary set that all users can access.
    This set serves as an example for new users.
    """
    from app.models import VocabSet, Card
    from app.data.standard_sets import HAUPTSTAEDTE_DATA
    from datetime import datetime
    
    # Check if default set already exists
    default_set = VocabSet.query.filter_by(name="Hauptstaedte", is_shared=True).first()
    if default_set:
        return  # Already exists
    
    try:
        # Create the shared vocab set (user_id=None for shared sets)
        vocab_set = VocabSet(
            name="Hauptstaedte",
            user_id=None,
            is_shared=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.session.add(vocab_set)
        db.session.flush()  # Get the ID
        
        # Create cards
        for item in HAUPTSTAEDTE_DATA:
            card = Card(
                vocab_set_id=vocab_set.id,
                front=item['front'],
                back=item['back'],
                level=1,
                next_review=datetime.now()
            )
            db.session.add(card)
        
        db.session.commit()
        print(f"✓ Created default shared vocabulary set: Hauptstaedte with {len(HAUPTSTAEDTE_DATA)} cards")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating default vocab set: {e}")
