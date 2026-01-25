"""
Vocabulary Service - Business Logic Layer.
Adapted for SQLAlchemy.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from app.database import db
from app.models import VocabSet, Card
from app.services.sm2_algorithm import calculate_next_review, get_initial_interval_for_level
from app.utils.validators import validate_set_name, validate_quality_score, validate_card_front, validate_set_ownership
from app.utils.exceptions import VocabSetNotFoundError, CardNotFoundError, UnauthorizedAccessError

class VocabService:
    
    @staticmethod
    def get_all_set_names(user_id: str) -> List[Dict]:
        # Get user sets
        user_sets = VocabSet.query.filter_by(user_id=user_id).all()
        
        result = []
        for vset in user_sets:
            stats = vset.get_statistics()
            level_counts = stats['level_counts']
            max_level = max(level_counts.items(), key=lambda x: x[1])[0] if level_counts else 1
            
            result.append({
                'id': vset.id,
                'name': vset.name,
                'is_shared': vset.is_shared,
                'card_count': stats['total_cards'],
                'due_count': stats['due_cards'],
                'level_counts': level_counts,
                'max_level': max_level
            })
        return result

    @staticmethod
    def get_vocab_set(set_id: str, user_id: str) -> VocabSet:
        vset = VocabSet.query.get(set_id)
        if not vset:
            raise VocabSetNotFoundError(f"Set ID {set_id}")
            
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
        # Sort by shuffle_order if present, putting None at the end
        cards.sort(key=lambda x: (x.shuffle_order is None, x.shuffle_order))
        return [c.to_dict() for c in cards]

    @staticmethod
    def get_all_cards(set_id: str, user_id: str, wrong_only: bool = False) -> List[Dict]:
        vset = VocabService.get_vocab_set(set_id, user_id)
        cards = vset.get_all_cards()
        if wrong_only:
            cards = [c for c in cards if c.last_practice_wrong]
        
        # Sort by shuffle_order if present, putting None at the end
        cards.sort(key=lambda x: (x.shuffle_order is None, x.shuffle_order))
        return [c.to_dict() for c in cards]

    @staticmethod
    def update_card_performance(set_id: str, card_front: str, quality: int, user_id: str) -> Dict:
        card_front = validate_card_front(card_front)
        quality = validate_quality_score(quality)
        
        vset = VocabService.get_vocab_set(set_id, user_id)
        card = vset.find_card(card_front)
        
        if not card:
            raise CardNotFoundError(card_front, vset.name)
            
        current_level = card.level
        last_interval = get_initial_interval_for_level(current_level)
        
        new_level, interval_days, _ = calculate_next_review(
            quality=quality, level=current_level, last_interval=last_interval, ease_factor=2.5
        )
        
        # Calculate next review time
        next_review = datetime.utcnow() + timedelta(days=interval_days)
        
        # Update card
        card.level = new_level
        card.next_review = next_review
        
        # Update set updated_at
        vset.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return {
            'status': 'success',
            'card': card.to_dict(),
            'old_level': current_level,
            'new_level': new_level,
            'interval_days': interval_days
        }

    @staticmethod
    def delete_card(set_id: str, card_id: str, user_id: str) -> None:
        vset = VocabService.get_vocab_set(set_id, user_id) # checks access
        
        card = Card.query.get(card_id)
        if not card:
            raise ValueError("Card not found")
            
        if card.vocab_set_id != set_id:
             raise ValueError("Card not in this set")
             
        db.session.delete(card)
        vset.updated_at = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def rename_set(set_id: str, new_name: str, user_id: str) -> VocabSet:
        vset = VocabService.get_vocab_set(set_id, user_id)
        
        if vset.user_id != user_id:
            raise ValueError("Access denied")
            
        validate_set_name(new_name)
        
        vset.name = new_name
        vset.updated_at = datetime.utcnow()
        db.session.commit()
        return vset

    @staticmethod
    def create_user_set(user_id: str, set_name: str) -> VocabSet:
        set_name = validate_set_name(set_name)
        
        # Check existing
        if VocabSet.query.filter_by(name=set_name, user_id=user_id).first():
            from app.utils.exceptions import InvalidInputError
            raise InvalidInputError("set_name", "Set exists")
            
        vset = VocabSet(
            id=str(uuid.uuid4()),
            name=set_name,
            user_id=user_id,
            is_shared=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(vset)
        db.session.commit()
        return vset

    @staticmethod
    def add_card(set_id: str, front: str, back: str, user_id: str) -> Card:
        front = validate_card_front(front)
        
        vset = VocabService.get_vocab_set(set_id, user_id)
        if vset.find_card(front):
             from app.utils.exceptions import InvalidInputError
             raise InvalidInputError("front", "Card exists")
             
        card = Card(
            id=str(uuid.uuid4()),
            vocab_set_id=set_id,
            front=front,
            back=back,
            level=1,
            next_review=datetime.utcnow()
        )
        db.session.add(card)
        
        vset.updated_at = datetime.utcnow()
        db.session.commit()
        return card

    @staticmethod
    def delete_set(set_id: str, user_id: str) -> Dict:
        vset = VocabService.get_vocab_set(set_id, user_id)
        
        # Access check
        if not vset.is_shared and vset.user_id != user_id:
            raise UnauthorizedAccessError("vocabulary set", set_id)
        
        # Bulk delete cards first (faster than cascade for large sets)
        Card.query.filter_by(vocab_set_id=set_id).delete(synchronize_session=False)
        
        # Now delete the set
        db.session.delete(vset)
        db.session.commit()
        
        return {'status': 'success'}

    @staticmethod
    def get_statistics(set_id: str, user_id: str) -> Dict:
        """Get statistics for a vocabulary set."""
        vset = VocabService.get_vocab_set(set_id, user_id)
        return vset.get_statistics()

    @staticmethod
    def reset_set(set_id: str, user_id: str) -> Dict:
        """Reset all cards in a set to level 1."""
        vset = VocabService.get_vocab_set(set_id, user_id)
        
        # Bulk update all cards (faster than iterating for large sets)
        count = Card.query.filter_by(vocab_set_id=set_id).update(
            {'level': 1, 'next_review': datetime.utcnow()},
            synchronize_session=False
        )
        
        vset.updated_at = datetime.utcnow()
        db.session.commit()
        
        return {'status': 'success', 'message': f'Reset {count} cards to level 1'}

    @staticmethod
    def restore_card(set_id: str, card_front: str, level: int, next_review: str, user_id: str) -> Dict:
        """Restore a card to a previous state (for undo functionality)."""
        card_front = validate_card_front(card_front)
        
        vset = VocabService.get_vocab_set(set_id, user_id)
        card = vset.find_card(card_front)
        
        if not card:
            raise CardNotFoundError(card_front, vset.name)
        
        # Parse next_review from ISO format or use as is
        if isinstance(next_review, str):
            try:
                # Handle ISO format string
                next_review_date = datetime.fromisoformat(next_review.replace('Z', '+00:00'))
            except ValueError:
                # Fallback if format is different
                next_review_date = datetime.utcnow()
        else:
            next_review_date = next_review

        # Ensure naive datetime for SQLAlchemy if needed, or stick to UTC convention
        # We are using utcnow() everywhere, so we should convert to naive UTC or keep offset aware if DB supports it.
        # SQLite acts weird with TZs, Postgres is better. 
        # Safest is to strip TZ if present and assume UTC, or rely on drivers.
        # For this implementation, I'll rely on the object logic.
        
        if next_review_date.tzinfo:
            next_review_date = next_review_date.replace(tzinfo=None)

        
        card.level = level
        card.next_review = next_review_date
        
        vset.updated_at = datetime.utcnow()
        db.session.commit()
        
        return {
            'status': 'success',
            'card': card.to_dict()
        }

    @staticmethod
    def mark_practice_wrong(set_id: str, card_front: str, user_id: str) -> Dict:
        """Mark a card as answered incorrectly in practice mode."""
        card_front = validate_card_front(card_front)
        
        vset = VocabService.get_vocab_set(set_id, user_id)
        card = vset.find_card(card_front)
        
        if not card:
            raise CardNotFoundError(card_front, vset.name)
        
        card.last_practice_wrong = True
        vset.updated_at = datetime.utcnow()
        db.session.commit()
        
        return {
            'status': 'success',
            'card': card.to_dict()
        }

    @staticmethod
    def mark_practice_correct(set_id: str, card_front: str, user_id: str) -> Dict:
        """Mark a card as answered correctly in practice mode."""
        card_front = validate_card_front(card_front)
        
        vset = VocabService.get_vocab_set(set_id, user_id)
        card = vset.find_card(card_front)
        
        if not card:
            raise CardNotFoundError(card_front, vset.name)
        
        card.last_practice_wrong = False
        vset.updated_at = datetime.utcnow()
        db.session.commit()
        
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
        vset = VocabService.get_vocab_set(set_id, user_id)
        
        # Verify all cards belong to the set and update their order
        # We fetch all cards to minimize DB queries
        all_cards = {c.id: c for c in vset.get_all_cards()}
        
        updated_count = 0
        for index, card_id in enumerate(card_ids):
            if card_id in all_cards:
                all_cards[card_id].shuffle_order = index
                updated_count += 1
                
        db.session.commit()
        
        return {
            'status': 'success',
            'updated_count': updated_count
        }
