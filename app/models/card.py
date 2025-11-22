"""
Card model for vocabulary flashcards.

This module provides the Card model as a SQLAlchemy entity.
"""

from datetime import datetime
from app.database import db


class Card(db.Model):
    """Card model representing a single flashcard."""
    
    __tablename__ = 'cards'
    
    id = db.Column(db.Integer, primary_key=True)
    vocab_set_id = db.Column(db.Integer, db.ForeignKey('vocab_sets.id'), nullable=False)
    front = db.Column(db.Text, nullable=False)
    back = db.Column(db.Text, nullable=False)
    level = db.Column(db.Integer, nullable=False, default=1)
    next_review = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert card to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'front': self.front,
            'back': self.back,
            'level': self.level,
            'next_review': self.next_review.isoformat()
        }
    
    def is_due(self) -> bool:
        """Check if the card is due for review."""
        return self.next_review <= datetime.now()
    
    def __repr__(self):
        return f'<Card {self.id}: {self.front[:20]}...>'
