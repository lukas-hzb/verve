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
    import os
    db.init_app(app)
    
    # On Vercel, we avoid running create_all() and seeds on every cold start
    # to prevent database connection spikes (MaxClientsReached).
    # These should be run once during initial setup or via a migration script.
    if not os.environ.get('VERCEL'):
        with app.app_context():
            # Import models to ensure they're registered with SQLAlchemy
            from app.models import User, VocabSet, Card
            
            # Create all tables
            db.create_all()
            
            # Create default shared vocabulary set if it doesn't exist
            create_default_vocab_set()
    else:
        app.logger.info("Skipping DB schema check/seed on Vercel to optimize startup.")


def create_default_vocab_set() -> None:
    """
    Create missing shared templates for the standard vocabulary sets.
    """
    from app.models import VocabSet, Card
    from app.data.standard_sets import default_vocabularies
    import uuid
    from app.utils.time import utc_now
    
    try:
        for name, vocabulary in default_vocabularies().items():
            if VocabSet.query.filter_by(name=name, is_shared=True).first():
                continue
            set_id = str(uuid.uuid4())
            db.session.add(VocabSet(
                id=set_id, name=name, user_id=None, is_shared=True,
                created_at=utc_now(), updated_at=utc_now(),
            ))
            db.session.add_all([
                Card(id=str(uuid.uuid4()), vocab_set_id=set_id, front=front, back=back,
                     level=1, next_review=utc_now(), shuffle_order=index)
                for index, (front, back) in enumerate(vocabulary)
            ])
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
