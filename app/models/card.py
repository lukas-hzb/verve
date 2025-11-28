"""
Card model for vocabulary flashcards.
Adapted for Firestore.
"""

from datetime import datetime, timezone

class Card:
    """Card model representing a single flashcard."""
    
    def __init__(self, id=None, vocab_set_id=None, front=None, back=None, level=1, next_review=None):
        self.id = id
        self.vocab_set_id = vocab_set_id
        self.front = front
        self.back = back
        self.level = level
        self.next_review = next_review or datetime.now(timezone.utc)

    def to_dict(self):
        return {
            'vocab_set_id': self.vocab_set_id,
            'front': self.front,
            'back': self.back,
            'level': self.level,
            'next_review': self.next_review
        }

    @staticmethod
    def from_dict(id, data):
        if not data:
            return None
        return Card(
            id=id,
            vocab_set_id=data.get('vocab_set_id'),
            front=data.get('front'),
            back=data.get('back'),
            level=data.get('level', 1),
            next_review=data.get('next_review')
        )
    
    def is_due(self) -> bool:
        """Check if the card is due for review."""
        # Ensure next_review is timezone-aware if needed, or naive. 
        # Firestore returns timezone-aware datetimes.
        now = datetime.now().astimezone() if self.next_review.tzinfo else datetime.now()
        return self.next_review <= now
    
    def __repr__(self):
        return f'<Card {self.id}: {self.front[:20]}...>'
