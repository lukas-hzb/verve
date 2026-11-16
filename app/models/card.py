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
    front_format = db.Column(db.String(8), nullable=False, default='plain', server_default='plain')
    back_format = db.Column(db.String(8), nullable=False, default='plain', server_default='plain')
    import_key = db.Column(db.String(36), nullable=True)
    level = db.Column(db.Integer, nullable=False, default=1)
    next_review = db.Column(db.DateTime, nullable=False, default=utc_now)
    interval_days = db.Column(db.Integer, nullable=True)
    ease_factor = db.Column(db.Float, nullable=True)
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
            'front_format': self.front_format,
            'back_format': self.back_format,
            'import_key': self.import_key,
            'level': self.level,
            'next_review': self.next_review.isoformat() if self.next_review else None,
            'interval_days': self.interval_days,
            'ease_factor': self.ease_factor,
            'last_practice_wrong': self.last_practice_wrong,
            # The existing DB column now remembers the last answer in either mode.
            'last_answer_wrong': self.last_practice_wrong,
            'shuffle_order': self.shuffle_order
        }

    def __repr__(self):
        return f'<Card {self.id}: {self.front[:20]}...>'


class CardReview(db.Model):
    __tablename__ = 'card_reviews'

    id = db.Column(db.String(36), primary_key=True)
    card_id = db.Column(db.String(36), db.ForeignKey('cards.id', ondelete='CASCADE'), nullable=False)
    reviewed_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    quality = db.Column(db.Integer, nullable=False)
    mode = db.Column(db.String(8), nullable=False)
    before_state = db.Column(db.JSON, nullable=False)
    after_state = db.Column(db.JSON, nullable=False)
    undone_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (Index('ix_card_reviews_card_time', 'card_id', 'reviewed_at'),)
