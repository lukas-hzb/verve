import uuid
from sqlalchemy import CheckConstraint, Index

from app.database import db
from app.utils.time import utc_now

class Card(db.Model):
    """Card model representing a single flashcard."""
    __tablename__ = 'cards'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vocab_set_id = db.Column(db.String(36), db.ForeignKey('vocab_sets.id'), nullable=False)
    front = db.Column(db.String(255), nullable=False)
    back = db.Column(db.Text, nullable=False)
    level = db.Column(db.Integer, nullable=False, default=1)
    next_review = db.Column(db.DateTime, nullable=False, default=utc_now)
    last_practice_wrong = db.Column(db.Boolean, nullable=False, default=False)
    shuffle_order = db.Column(db.Integer, nullable=True)  # For persistent shuffle order

    __table_args__ = (
        CheckConstraint('level >= 1', name='ck_cards_level_positive'),
        Index('ix_cards_set_due', 'vocab_set_id', 'next_review'),
        Index('ix_cards_set_shuffle', 'vocab_set_id', 'shuffle_order'),
    )

    def is_due(self) -> bool:
        """Check if the card is due for review."""
        return self.next_review <= utc_now()
    
    def to_dict(self):
        return {
            'id': self.id,
            'vocab_set_id': self.vocab_set_id,
            'front': self.front,
            'back': self.back,
            'level': self.level,
            'next_review': self.next_review.isoformat() if self.next_review else None,
            'last_practice_wrong': self.last_practice_wrong,
            'shuffle_order': self.shuffle_order
        }

    def __repr__(self):
        return f'<Card {self.id}: {self.front[:20]}...>'
