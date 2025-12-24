from datetime import datetime
from typing import List, Optional
from app.database import db

class VocabSet(db.Model):
    """Represents a vocabulary set."""
    __tablename__ = 'vocab_sets'

    id = db.Column(db.String(36), primary_key=True) # UUID
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True) # Null for shared sets
    is_shared = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cards = db.relationship('Card', backref='vocab_set', lazy='dynamic', cascade='all, delete-orphan')

    def get_due_cards(self) -> List['Card']:
        """Get all cards that are due for review."""
        return [card for card in self.cards if card.is_due()]
    
    def get_all_cards(self) -> List['Card']:
        """Get all cards in the set."""
        return self.cards.all()
    
    def find_card(self, front: str) -> Optional['Card']:
        return self.cards.filter_by(front=front).first()
    
    def get_statistics(self) -> dict:
        cards_list = self.cards.all()
        level_counts = {}
        due_count = 0
        for card in cards_list:
            level = card.level
            level_counts[level] = level_counts.get(level, 0) + 1
            if card.is_due():
                due_count += 1
        
        return {
            'total_cards': len(cards_list),
            'level_counts': level_counts,
            'due_cards': due_count
        }
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'user_id': self.user_id,
            'is_shared': self.is_shared,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def __repr__(self):
        return f'<VocabSet {self.name}>'
