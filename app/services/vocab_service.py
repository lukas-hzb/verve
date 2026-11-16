"""
Vocabulary Service - Business Logic Layer.
Adapted for SQLAlchemy.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.models import VocabSet, Card
from app.models.card import CardReview
from app.services.sm2_algorithm import calculate_next_review, get_initial_interval_for_level
from app.utils.time import utc_now
from app.utils.validators import (
    encode_card_line_breaks,
    validate_card_back,
    validate_card_front,
    validate_card_level,
    validate_card_source,
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
            display_counts = {}
            for level, count in level_counts.items():
                display_level = max(1, min(level, 5))
                display_counts[display_level] = display_counts.get(display_level, 0) + count
            max_level = max(display_counts, key=display_counts.get) if display_counts else 1
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
    def get_vocab_set(set_id: str, user_id: str, *, require_owner: bool = False,
                      for_update: bool = False) -> VocabSet:
        """Load a set and enforce either readable or owner-only access."""
        vset = db.session.get(VocabSet, set_id, with_for_update=for_update)
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
    def get_all_cards(set_id: str, user_id: str, wrong_only: bool = False, last_wrong_only: bool = False) -> List[Dict]:
        vset = VocabService.get_vocab_set(set_id, user_id)
        cards = vset.get_all_cards(wrong_only=wrong_only, last_wrong_only=last_wrong_only)
        return [c.to_dict() for c in cards]

    @staticmethod
    def _review_card(set_id, user_id, card_id, card_front):
        if card_id is not None and (not isinstance(card_id, str) or not 1 <= len(card_id) <= 36):
            raise InvalidInputError('card_id', 'Invalid card ID')
        vocab_set = VocabService.get_vocab_set(set_id, user_id, require_owner=True, for_update=True)
        query = vocab_set.cards
        if card_id is None:
            query = query.filter_by(front=validate_card_front(card_front))
        else:
            query = query.filter_by(id=card_id)
        card = query.with_for_update().first()
        if not card:
            raise CardNotFoundError(card_id or card_front, vocab_set.name)
        return vocab_set, card

    @staticmethod
    def _review_state(card):
        return {
            'level': card.level,
            'next_review': card.next_review.isoformat(),
            'interval_days': card.interval_days,
            'ease_factor': card.ease_factor,
            'last_practice_wrong': card.last_practice_wrong,
        }

    @staticmethod
    def _review_result(card, review):
        return {
            'status': 'success',
            'card': card.to_dict(),
            'old_level': review.before_state['level'],
            'new_level': review.after_state['level'],
            'interval_days': review.after_state['interval_days'],
            'review_id': review.id,
        }

    @staticmethod
    def record_answer(set_id, card_front, quality, user_id, *, card_id=None, review_id=None, mode='study'):
        quality = validate_quality_score(quality)
        try:
            review_id = str(uuid.UUID(review_id)) if review_id is not None else str(uuid.uuid4())
        except (TypeError, ValueError, AttributeError):
            raise InvalidInputError('review_id', 'Invalid review ID') from None

        vocab_set, card = VocabService._review_card(set_id, user_id, card_id, card_front)
        existing = db.session.get(CardReview, review_id)
        if existing:
            if (existing.card_id, existing.quality, existing.mode) != (card.id, quality, mode):
                raise InvalidInputError('review_id', 'This review ID is already in use')
            return VocabService._review_result(card, existing)

        now = utc_now()
        before = VocabService._review_state(card)
        if mode == 'study':
            level, interval, ease = calculate_next_review(
                quality, card.level, card.interval_days or get_initial_interval_for_level(card.level),
                card.ease_factor if card.ease_factor is not None else 2.5,
            )
            interval = min(interval, 36500)
            card.level = level
            card.interval_days = interval
            card.ease_factor = ease
            card.next_review = now + timedelta(days=interval)
        card.last_practice_wrong = quality < 3
        review = CardReview(id=review_id, card_id=card.id, quality=quality, mode=mode, reviewed_at=now,
                            before_state=before, after_state=VocabService._review_state(card))
        db.session.add(review)
        vocab_set.updated_at = now
        VocabService._commit()
        return VocabService._review_result(card, review)

    @staticmethod
    def update_card_performance(set_id, card_front, quality, user_id, *, card_id=None, review_id=None):
        return VocabService.record_answer(set_id, card_front, quality, user_id, card_id=card_id, review_id=review_id)

    @staticmethod
    def undo_answer(set_id, card_id, review_id, user_id):
        try:
            review_id = str(uuid.UUID(review_id))
        except (TypeError, ValueError, AttributeError):
            raise InvalidInputError('review_id', 'Invalid review ID') from None
        vocab_set, card = VocabService._review_card(set_id, user_id, card_id, None)
        review = CardReview.query.filter_by(id=review_id, card_id=card.id).first()
        if review and not review.undone_at:
            latest = CardReview.query.filter_by(card_id=card.id, undone_at=None).order_by(
                CardReview.reviewed_at.desc(), CardReview.id.desc()
            ).first()
            if latest.id != review.id or VocabService._review_state(card) != review.after_state:
                raise InvalidInputError('review_id', 'Card progress has changed since this answer')
            for key, value in review.before_state.items():
                setattr(card, key, datetime.fromisoformat(value) if key == 'next_review' else value)
            review.undone_at = vocab_set.updated_at = utc_now()
            VocabService._commit()
        return {'status': 'success', 'card': card.to_dict()}

    @staticmethod
    def edit_card(set_id: str, card_id: str, front: str, back: str, user_id: str, *,
                  front_format=None, back_format=None) -> Card:
        vset = VocabService.get_vocab_set(set_id, user_id, require_owner=True)
        card = Card.query.filter_by(id=card_id, vocab_set_id=set_id).first()
        if not card:
            raise CardNotFoundError(card_id, vset.name)

        front_format = card.front_format if front_format is None else front_format
        back_format = card.back_format if back_format is None else back_format
        front = validate_card_source(front, front_format, front=True)
        back = validate_card_source(back, back_format)
        duplicate = Card.query.filter_by(vocab_set_id=set_id, front=front).filter(Card.id != card_id).first()
        if duplicate:
            raise InvalidInputError("front", "Another Card already uses this Front")

        card.front = front
        card.back = back
        card.front_format = front_format
        card.back_format = back_format
        vset.updated_at = utc_now()
        VocabService._commit()
        return card

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
    def set_text_alignment(set_id: str, alignment: str, user_id: str) -> None:
        VocabService.set_text_layout(set_id, 'text_alignment', alignment, user_id)

    @staticmethod
    def set_text_layout(set_id: str, setting: str, value: str, user_id: str) -> None:
        vset = VocabService.get_vocab_set(set_id, user_id, require_owner=True)
        choices = {
            'text_alignment': ('left', 'center'),
            'text_scaling': ('auto', 'minimum'),
            'text_vertical_alignment': ('center', 'top'),
        }
        if not isinstance(setting, str) or value not in choices.get(setting, ()):
            raise InvalidInputError('text_layout', 'Invalid text layout option')
        setattr(vset, setting, value)
        VocabService._commit()

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
    def add_card(set_id: str, front: str, back: str, user_id: str, *,
                 front_format='plain', back_format='plain') -> Card:
        front = validate_card_source(front, front_format, front=True)
        back = validate_card_source(back, back_format)

        vset = VocabService.get_vocab_set(set_id, user_id, require_owner=True)
        if vset.find_card(front) or (front_format == 'plain' and r'\n' in front and any(
            encode_card_line_breaks(legacy_front) == front
            for (legacy_front,) in vset.cards.filter_by(front_format='plain').with_entities(Card.front)
        )):
            raise InvalidInputError("front", "Card exists")
             
        card = Card(
            id=str(uuid.uuid4()),
            vocab_set_id=set_id,
            front=front,
            back=back,
            front_format=front_format,
            back_format=back_format,
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
        stats = vset.get_statistics()
        display_counts = {}
        for level, count in stats['level_counts'].items():
            display_level = max(1, min(level, 5))
            display_counts[display_level] = display_counts.get(display_level, 0) + count
        stats['level_counts'] = display_counts
        return stats

    @staticmethod
    def reset_set(set_id: str, user_id: str) -> Dict:
        """Reset all cards in a set to level 1."""
        vset = VocabService.get_vocab_set(set_id, user_id, require_owner=True, for_update=True)
        
        # Bulk update all cards (faster than iterating for large sets)
        count = Card.query.filter_by(vocab_set_id=set_id).update(
            {'level': 1, 'next_review': utc_now(), 'interval_days': None, 'ease_factor': None},
            synchronize_session=False
        )
        
        vset.updated_at = utc_now()
        VocabService._commit()
        
        return {'status': 'success', 'message': f'Reset {count} Cards to Level 1'}

    @staticmethod
    def restore_card(set_id: str, card_front: str, level: int, next_review: str, user_id: str, last_answer_wrong: Optional[bool] = None) -> Dict:
        """Restore a card to a previous state (for undo functionality)."""
        card_front = validate_card_front(card_front)
        level = validate_card_level(level)
        if last_answer_wrong is not None and not isinstance(last_answer_wrong, bool):
            raise InvalidInputError('last_answer_wrong', 'Must be a boolean')

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
                raise InvalidInputError('next_review', 'Invalid ISO Date')
        else:
            next_review_date = next_review

        if not hasattr(next_review_date, 'tzinfo'):
            raise InvalidInputError('next_review', 'Invalid Date Value')
        if next_review_date.tzinfo:
            from datetime import UTC
            next_review_date = next_review_date.astimezone(UTC).replace(tzinfo=None)

        
        card.level = level
        card.next_review = next_review_date
        if last_answer_wrong is not None:
            card.last_practice_wrong = last_answer_wrong
        
        vset.updated_at = utc_now()
        VocabService._commit()
        
        return {
            'status': 'success',
            'card': card.to_dict()
        }

    @staticmethod
    def mark_practice_wrong(set_id, card_front, user_id, *, card_id=None, review_id=None):
        return VocabService.record_answer(set_id, card_front, 2, user_id, card_id=card_id,
                                         review_id=review_id, mode='practice')

    @staticmethod
    def mark_practice_correct(set_id, card_front, user_id, *, card_id=None, review_id=None):
        return VocabService.record_answer(set_id, card_front, 5, user_id, card_id=card_id,
                                         review_id=review_id, mode='practice')

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
            raise InvalidInputError('card_ids', 'One or more Cards do not belong to this Set')

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
