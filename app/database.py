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
    from pathlib import Path
    import pandas as pd
    from datetime import datetime
    
    # Check if default set already exists
    default_set = VocabSet.query.filter_by(name="Hauptstaedte", is_shared=True).first()
    if default_set:
        return  # Already exists
    
    # Path to the TSV file
    tsv_path = Path(__file__).parent.parent / "vocab_sets" / "Hauptstaedte.tsv"
    
    if not tsv_path.exists():
        print(f"Warning: Default vocab set file not found at {tsv_path}")
        return
    
    try:
        # Read TSV file
        df = pd.read_csv(
            tsv_path,
            sep='\t',
            header=None,
            on_bad_lines='skip',
            quoting=3
        )
        
        if df.empty or df.shape[1] < 2:
            print("Warning: Default vocab set file is empty or invalid")
            return
        
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
        
        # Assign column names
        df.columns = ["front", "back", "level", "next_review"][:df.shape[1]]
        
        # Add missing columns with defaults
        if 'level' not in df.columns:
            df['level'] = 1
        if 'next_review' not in df.columns:
            df['next_review'] = datetime.now()
        
        # Convert types
        df['level'] = pd.to_numeric(df['level'], errors='coerce').fillna(1).astype(int)
        df['next_review'] = pd.to_datetime(df['next_review'], errors='coerce').fillna(datetime.now())
        
        # Remove rows with missing front or back
        df = df.dropna(subset=["front", "back"])
        
        # Create cards
        for _, row in df.iterrows():
            card = Card(
                vocab_set_id=vocab_set.id,
                front=str(row['front']),
                back=str(row['back']),
                level=int(row['level']),
                next_review=row['next_review']
            )
            db.session.add(card)
        
        db.session.commit()
        print(f"✓ Created default shared vocabulary set: Hauptstaedte with {len(df)} cards")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating default vocab set: {e}")
