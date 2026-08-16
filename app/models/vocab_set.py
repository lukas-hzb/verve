from typing import List, Optional
import uuid
from sqlalchemy import CheckConstraint, Index, UniqueConstraint, case, func, or_

from app.database import db
from app.utils.time import utc_now

class VocabSet(db.Model):
    """Represents a vocabulary set."""
    __tablename__ = 'vocab_sets'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True) # Null for shared sets
    is_shared = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_vocab_sets_user_name'),
        CheckConstraint(
            '(is_shared AND user_id IS NULL) OR (NOT is_shared AND user_id IS NOT NULL)',
            name='ck_vocab_sets_owner_or_shared',
        ),
        Index('ix_vocab_sets_user_id', 'user_id'),
    )

    # Relationships
    cards = db.relationship('Card', backref='vocab_set', lazy='dynamic', cascade='all, delete-orphan')

    def get_due_cards(self) -> List['Card']:
        """Get all cards that are due for review."""
        from app.models.card import Card

        return self.cards.filter(Card.next_review <= utc_now()).order_by(
            Card.shuffle_order.is_(None),
            Card.shuffle_order,
            Card.id,
        ).all()
    
    def get_all_cards(self, *, wrong_only: bool = False) -> List['Card']:
        """Get all cards in the set."""
        from app.models.card import Card

        query = self.cards
        if wrong_only:
            query = query.filter(or_(Card.last_practice_wrong.is_(True), Card.level == 1))
        return query.order_by(
            Card.shuffle_order.is_(None),
            Card.shuffle_order,
            Card.id,
        ).all()
    
    def find_card(self, front: str) -> Optional['Card']:
        return self.cards.filter_by(front=front).first()
    
    def get_statistics(self) -> dict:
        from app.models.card import Card

        rows = db.session.query(
            Card.level,
            func.count(Card.id),
            func.sum(case((Card.next_review <= utc_now(), 1), else_=0)),
        ).filter(Card.vocab_set_id == self.id).group_by(Card.level).all()

        level_counts = {level: count for level, count, _ in rows}
        return {
            'total_cards': sum(level_counts.values()),
            'level_counts': level_counts,
            'due_cards': sum(due_count or 0 for _, _, due_count in rows),
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
