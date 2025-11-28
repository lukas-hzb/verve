"""
Vocabulary Set Data Model.
Adapted for Firestore.
"""

from datetime import datetime
from typing import List, Optional

class VocabSet:
    """Represents a vocabulary set."""
    
    def __init__(self, id=None, name=None, user_id=None, is_shared=False, created_at=None, updated_at=None):
        self.id = id
        self.name = name
        self.user_id = user_id
        self.is_shared = is_shared
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.cards = []  # Will be populated separately if needed

    def to_dict(self):
        return {
            'name': self.name,
            'user_id': self.user_id,
            'is_shared': self.is_shared,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def from_dict(id, data):
        if not data:
            return None
        return VocabSet(
            id=id,
            name=data.get('name'),
            user_id=data.get('user_id'),
            is_shared=data.get('is_shared', False),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def get_due_cards(self) -> List['Card']:
        """Get all cards that are due for review."""
        return [card for card in self.cards if card.is_due()]
    
    def get_all_cards(self) -> List['Card']:
        """Get all cards in the set."""
        return self.cards
    
    def find_card(self, front: str) -> Optional['Card']:
        for card in self.cards:
            if card.front == front:
                return card
        return None
    
    def get_statistics(self) -> dict:
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
