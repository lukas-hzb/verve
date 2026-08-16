"""
Vocabulary Service - Business Logic Layer.
Adapted for SQLAlchemy.
"""

import uuid
from datetime import timedelta
from typing import List, Dict, Optional

from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.models import VocabSet, Card
from app.services.sm2_algorithm import calculate_next_review, get_initial_interval_for_level
from app.utils.time import utc_now
from app.utils.validators import (
    validate_card_back,
    validate_card_front,
    validate_card_level,
    validate_quality_score,
    validate_set_name,
    validate_set_ownership,
)
from app.utils.exceptions import (
    CardNotFoundError,
    InvalidInputError,
    UnauthorizedAccessError,
    VocabSetNotFoundError,
)

class VocabService:
    
    @staticmethod
    def get_all_set_names(user_id: str) -> List[Dict]:
        """Return all sidebar sets with statistics in two queries, not N+1."""
        user_sets = VocabSet.query.filter_by(user_id=user_id).order_by(VocabSet.created_at).all()
        if not user_sets:
            return []

        now = utc_now()
        set_ids = [vocab_set.id for vocab_set in user_sets]
        statistic_rows = db.session.query(
            Card.vocab_set_id,
            Card.level,
            func.count(Card.id),
            func.sum(case((Card.next_review <= now, 1), else_=0)),
        ).filter(Card.vocab_set_id.in_(set_ids)).group_by(
            Card.vocab_set_id,
            Card.level,
        ).all()

        statistics = {
            set_id: {'card_count': 0, 'due_count': 0, 'level_counts': {}}
            for set_id in set_ids
        }
        for set_id, level, card_count, due_count in statistic_rows:
            statistics[set_id]['card_count'] += card_count
            statistics[set_id]['due_count'] += due_count or 0
            statistics[set_id]['level_counts'][level] = card_count

        result = []
        for vocab_set in user_sets:
            stats = statistics[vocab_set.id]
            level_counts = stats['level_counts']
            max_level = max(level_counts, key=level_counts.get) if level_counts else 1
            result.append({
                'id': vocab_set.id,
                'name': vocab_set.name,
                'is_shared': vocab_set.is_shared,
                'card_count': stats['card_count'],
                'due_count': stats['due_count'],
                'level_counts': level_counts,
                'max_level': max_level
            })
        return result

    @staticmethod
    def get_vocab_set(set_id: str, user_id: str, *, require_owner: bool = False) -> VocabSet:
        """Load a set and enforce either readable or owner-only access."""
        vset = db.session.get(VocabSet, set_id)
        if not vset:
            raise VocabSetNotFoundError(f"Set ID {set_id}")

        if require_owner:
            if vset.user_id != user_id:
                raise UnauthorizedAccessError("vocabulary set", set_id)
        else:
            validate_set_ownership(user_id, vset)
        return vset

    @staticmethod
    def get_vocab_set_by_name(set_name: str, user_id: str) -> Optional[VocabSet]:
        set_name = validate_set_name(set_name)
        
        # Try user set
        vset = VocabSet.query.filter_by(name=set_name, user_id=user_id).first()
        if vset:
            return vset
            
        # Try shared set
        vset = VocabSet.query.filter_by(name=set_name, is_shared=True).first()
        if vset:
            return vset
            
        return None

    @staticmethod
    def get_due_cards(set_id: str, user_id: str) -> List[Dict]:
        vset = VocabService.get_vocab_set(set_id, user_id)
        cards = vset.get_due_cards()
        return [c.to_dict() for c in cards]

    @staticmethod
    def get_all_cards(set_id: str, user_id: str, wrong_only: bool = False) -> List[Dict]:
        vset = VocabService.get_vocab_set(set_id, user_id)
        cards = vset.get_all_cards(wrong_only=wrong_only)
        return [c.to_dict() for c in cards]

    @staticmethod
    def update_card_performance(set_id: str, card_front: str, quality: int, user_id: str) -> Dict:
        card_front = validate_card_front(card_front)
        quality = validate_quality_score(quality)
        
        vset = VocabService.get_vocab_set(set_id, user_id, require_owner=True)
        card = vset.find_card(card_front)
        
        if not card:
            raise CardNotFoundError(card_front, vset.name)
            
        current_level = card.level
        last_interval = get_initial_interval_for_level(current_level)
        
        new_level, interval_days, _ = calculate_next_review(
            quality=quality, level=current_level, last_interval=last_interval, ease_factor=2.5
        )
        
        # Calculate next review time
        next_review = utc_now() + timedelta(days=interval_days)
        
        # Update card
        card.level = new_level
        card.next_review = next_review
        
        # Update set updated_at
        vset.updated_at = utc_now()
        VocabService._commit()
        
        return {
            'status': 'success',
            'card': card.to_dict(),
            'old_level': current_level,
            'new_level': new_level,
            'interval_days': interval_days
        }

    @staticmethod
    def delete_card(set_id: str, card_id: str, user_id: str) -> None:
        vset = VocabService.get_vocab_set(set_id, user_id, require_owner=True)

        card = Card.query.filter_by(id=card_id, vocab_set_id=set_id).first()
        if not card:
            raise CardNotFoundError(card_id, vset.name)

        db.session.delete(card)
        vset.updated_at = utc_now()
        VocabService._commit()

    @staticmethod
    def rename_set(set_id: str, new_name: str, user_id: str) -> VocabSet:
        vset = VocabService.get_vocab_set(set_id, user_id, require_owner=True)
        new_name = validate_set_name(new_name)

        vset.name = new_name
        vset.updated_at = utc_now()
        VocabService._commit()
        return vset

    @staticmethod
    def create_user_set(user_id: str, set_name: str, *, commit: bool = True) -> VocabSet:
        set_name = validate_set_name(set_name)
        
        # Check existing
        if VocabSet.query.filter_by(name=set_name, user_id=user_id).first():
            raise InvalidInputError("set_name", "Set exists")
            
        vset = VocabSet(
            id=str(uuid.uuid4()),
            name=set_name,
            user_id=user_id,
            is_shared=False,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.session.add(vset)
        try:
            if commit:
                VocabService._commit()
            else:
                db.session.flush()
        except IntegrityError:
            db.session.rollback()
            raise InvalidInputError("set_name", "Set exists")
        return vset

    @staticmethod
    def add_card(set_id: str, front: str, back: str, user_id: str) -> Card:
        front = validate_card_front(front)
        back = validate_card_back(back)

        vset = VocabService.get_vocab_set(set_id, user_id, require_owner=True)
        if vset.find_card(front):
            raise InvalidInputError("front", "Card exists")
             
        card = Card(
            id=str(uuid.uuid4()),
            vocab_set_id=set_id,
            front=front,
            back=back,
            level=1,
            next_review=utc_now()
        )
        db.session.add(card)
        
        vset.updated_at = utc_now()
        VocabService._commit()
        return card

    @staticmethod
    def delete_set(set_id: str, user_id: str) -> Dict:
        vset = VocabService.get_vocab_set(set_id, user_id, require_owner=True)
        
        # Bulk delete cards first (faster than cascade for large sets)
        Card.query.filter_by(vocab_set_id=set_id).delete(synchronize_session=False)
        
        # Now delete the set
        db.session.delete(vset)
        VocabService._commit()
        
        return {'status': 'success'}

    @staticmethod
    def get_statistics(set_id: str, user_id: str) -> Dict:
        """Get statistics for a vocabulary set."""
        vset = VocabService.get_vocab_set(set_id, user_id)
        return vset.get_statistics()

    @staticmethod
    def reset_set(set_id: str, user_id: str) -> Dict:
        """Reset all cards in a set to level 1."""
        vset = VocabService.get_vocab_set(set_id, user_id, require_owner=True)
        
        # Bulk update all cards (faster than iterating for large sets)
        count = Card.query.filter_by(vocab_set_id=set_id).update(
            {'level': 1, 'next_review': utc_now()},
            synchronize_session=False
        )
        
        vset.updated_at = utc_now()
        VocabService._commit()
        
        return {'status': 'success', 'message': f'Reset {count} cards to level 1'}

    @staticmethod
    def restore_card(set_id: str, card_front: str, level: int, next_review: str, user_id: str) -> Dict:
        """Restore a card to a previous state (for undo functionality)."""
        card_front = validate_card_front(card_front)
        level = validate_card_level(level)

        vset = VocabService.get_vocab_set(set_id, user_id, require_owner=True)
        card = vset.find_card(card_front)
        
        if not card:
            raise CardNotFoundError(card_front, vset.name)
        
        # Parse next_review from ISO format or use as is.
        if isinstance(next_review, str):
            try:
                from datetime import datetime
                next_review_date = datetime.fromisoformat(next_review.replace('Z', '+00:00'))
            except ValueError:
                raise InvalidInputError('next_review', 'Invalid ISO date')
        else:
            next_review_date = next_review

        if not hasattr(next_review_date, 'tzinfo'):
            raise InvalidInputError('next_review', 'Invalid date value')
        if next_review_date.tzinfo:
            from datetime import UTC
            next_review_date = next_review_date.astimezone(UTC).replace(tzinfo=None)

        
        card.level = level
        card.next_review = next_review_date
        
        vset.updated_at = utc_now()
        VocabService._commit()
        
        return {
            'status': 'success',
            'card': card.to_dict()
        }

    @staticmethod
    def mark_practice_wrong(set_id: str, card_front: str, user_id: str) -> Dict:
        """Mark a card as answered incorrectly in practice mode."""
        card_front = validate_card_front(card_front)
        
        vset = VocabService.get_vocab_set(set_id, user_id, require_owner=True)
        card = vset.find_card(card_front)
        
        if not card:
            raise CardNotFoundError(card_front, vset.name)
        
        card.last_practice_wrong = True
        vset.updated_at = utc_now()
        VocabService._commit()
        
        return {
            'status': 'success',
            'card': card.to_dict()
        }

    @staticmethod
    def mark_practice_correct(set_id: str, card_front: str, user_id: str) -> Dict:
        """Mark a card as answered correctly in practice mode."""
        card_front = validate_card_front(card_front)
        
        vset = VocabService.get_vocab_set(set_id, user_id, require_owner=True)
        card = vset.find_card(card_front)
        
        if not card:
            raise CardNotFoundError(card_front, vset.name)
        
        card.last_practice_wrong = False
        vset.updated_at = utc_now()
        VocabService._commit()
        
        return {
            'status': 'success',
            'card': card.to_dict()
        }

    @staticmethod
    def save_shuffle_order(set_id: str, card_ids: List[str], user_id: str) -> Dict:
        """
        Save the specific order of cards for a set.
        
        Args:
            set_id: The ID of the vocabulary set
            card_ids: List of card IDs in the desired order
            user_id: The ID of the requesting user
        """
        vset = VocabService.get_vocab_set(set_id, user_id, require_owner=True)
        if not isinstance(card_ids, list) or not all(isinstance(card_id, str) for card_id in card_ids):
            raise InvalidInputError('card_ids', 'card_ids must be a list of IDs')
        if len(card_ids) != len(set(card_ids)):
            raise InvalidInputError('card_ids', 'card_ids must not contain duplicates')

        # Verify all cards belong to the set and update their order
        # We fetch all cards to minimize DB queries
        all_cards = {c.id: c for c in vset.get_all_cards()}
        
        unknown_ids = set(card_ids) - set(all_cards)
        if unknown_ids:
            raise InvalidInputError('card_ids', 'One or more cards do not belong to this set')

        for index, card_id in enumerate(card_ids):
            all_cards[card_id].shuffle_order = index

        vset.updated_at = utc_now()
        VocabService._commit()
        
        return {
            'status': 'success',
            'updated_count': len(card_ids)
        }

    @staticmethod
    def _commit() -> None:
        """Commit one service operation and leave no failed transaction behind."""
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
