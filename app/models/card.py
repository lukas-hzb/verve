from datetime import datetime
from app.database import db

class Card(db.Model):
    """Card model representing a single flashcard."""
    __tablename__ = 'cards'

    id = db.Column(db.String(36), primary_key=True) # UUID
    vocab_set_id = db.Column(db.String(36), db.ForeignKey('vocab_sets.id'), nullable=False)
    front = db.Column(db.String(255), nullable=False)
    back = db.Column(db.Text, nullable=False)
    level = db.Column(db.Integer, default=1)
    next_review = db.Column(db.DateTime, default=datetime.utcnow)

    def is_due(self) -> bool:
        """Check if the card is due for review."""
        return self.next_review <= datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'vocab_set_id': self.vocab_set_id,
            'front': self.front,
            'back': self.back,
            'level': self.level,
            'next_review': self.next_review
        }

    def __repr__(self):
        return f'<Card {self.id}: {self.front[:20]}...>'
