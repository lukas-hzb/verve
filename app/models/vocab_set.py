"""
Vocabulary Set Data Model.

This module provides the SQLAlchemy model for vocabulary sets,
replacing the previous dataclass-based implementation.
"""

from datetime import datetime
from typing import List, Optional
from app.database import db


class VocabSet(db.Model):
    """Represents a vocabulary set with multiple cards."""
    
    __tablename__ = 'vocab_sets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # None for shared sets
    is_shared = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    cards = db.relationship('Card', backref='vocab_set', lazy=True, cascade='all, delete-orphan')
    
    def get_due_cards(self) -> List['Card']:
        """Get all cards that are due for review."""
        from app.models.card import Card
        return [card for card in self.cards if card.is_due()]
    
    def get_all_cards(self) -> List['Card']:
        """Get all cards in the set."""
        return self.cards
    
    def find_card(self, front: str) -> Optional['Card']:
        """
        Find a card by its front text.
        
        Args:
            front: The front text of the card to find
            
        Returns:
            The card if found, None otherwise
        """
        for card in self.cards:
            if card.front == front:
                return card
        return None
    
    def update_card(self, front: str, level: int, next_review: datetime) -> None:
        """
        Update a card's review data.
        
        Args:
            front: The front text of the card to update
            level: New level for the card
            next_review: New next review date
            
        Raises:
            CardNotFoundError: If the card is not found
        """
        from app.utils.exceptions import CardNotFoundError
        
        card = self.find_card(front)
        if card is None:
            raise CardNotFoundError(front, self.name)
        
        card.level = level
        card.next_review = next_review
        self.updated_at = datetime.now()
        db.session.commit()
    
    def reset_all_cards(self) -> None:
        """Reset all cards to level 1 with immediate review."""
        for card in self.cards:
            card.level = 1
            card.next_review = datetime.now()
        self.updated_at = datetime.now()
        db.session.commit()
    
    def get_statistics(self) -> dict:
        """
        Get statistics about the vocabulary set.
        
        Returns:
            Dictionary with statistics including total cards and level distribution
        """
        level_counts = {}
        for card in self.cards:
            level = card.level
            level_counts[level] = level_counts.get(level, 0) + 1
        
        return {
            'total_cards': len(self.cards),
            'level_counts': level_counts,
            'due_cards': len(self.get_due_cards())
        }
    
    def __repr__(self):
        return f'<VocabSet {self.name}>'
