"""
Vocabulary Service - Business Logic Layer.
Adapted for Firestore.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from google.cloud.firestore_v1.base_query import FieldFilter

from app.firestore_db import get_db
from app.models import VocabSet, Card
from app.services.sm2_algorithm import calculate_next_review, get_initial_interval_for_level
from app.utils.validators import validate_set_name, validate_quality_score, validate_card_front, validate_set_ownership
from app.utils.exceptions import VocabSetNotFoundError, CardNotFoundError, UnauthorizedAccessError

class VocabService:
    
    @staticmethod
    def get_all_set_names(user_id: str) -> List[Dict]:
        db = get_db()
        # Get user sets
        sets_stream = db.collection('sets').where('user_id', '==', user_id).stream()
        
        result = []
        for doc in sets_stream:
            vset = VocabSet.from_dict(doc.id, doc.to_dict())
            
            # Get cards for this set to calc stats
            # Note: This is N+1 query, but Firestore is fast. 
            # For optimization, we could store stats on the set document.
            cards = list(db.collection('cards').where('vocab_set_id', '==', vset.id).stream())
            vset.cards = [Card.from_dict(c.id, c.to_dict()) for c in cards]
            
            stats = vset.get_statistics()
            level_counts = stats['level_counts']
            max_level = max(level_counts.items(), key=lambda x: x[1])[0] if level_counts else 1
            
            result.append({
                'id': vset.id,
                'name': vset.name,
                'is_shared': vset.is_shared,
                'card_count': len(vset.cards),
                'due_count': stats['due_cards'],
                'level_counts': level_counts,
                'max_level': max_level
            })
        return result

    @staticmethod
    def get_vocab_set(set_id: str, user_id: str) -> VocabSet:
        db = get_db()
        doc = db.collection('sets').document(str(set_id)).get()
        if not doc.exists:
            raise VocabSetNotFoundError(f"Set ID {set_id}")
            
        vset = VocabSet.from_dict(doc.id, doc.to_dict())
        
        # Populate cards
        cards = list(db.collection('cards').where('vocab_set_id', '==', vset.id).stream())
        vset.cards = [Card.from_dict(c.id, c.to_dict()) for c in cards]
        
        validate_set_ownership(user_id, vset)
        return vset

    @staticmethod
    def get_vocab_set_by_name(set_name: str, user_id: str) -> Optional[VocabSet]:
        db = get_db()
        set_name = validate_set_name(set_name)
        
        # Try user set
        docs = list(db.collection('sets').where('name', '==', set_name)\
                    .where('user_id', '==', user_id).limit(1).stream())
        if docs:
            vset = VocabSet.from_dict(docs[0].id, docs[0].to_dict())
            # populate cards if needed
            return vset
            
        # Try shared set
        docs = list(db.collection('sets').where('name', '==', set_name)\
                    .where('is_shared', '==', True).limit(1).stream())
        if docs:
            return VocabSet.from_dict(docs[0].id, docs[0].to_dict())
            
        return None

    @staticmethod
    def get_due_cards(set_id: str, user_id: str) -> List[Dict]:
        vset = VocabService.get_vocab_set(set_id, user_id)
        return [c.to_dict() for c in vset.get_due_cards()]

    @staticmethod
    def get_all_cards(set_id: str, user_id: str) -> List[Dict]:
        vset = VocabService.get_vocab_set(set_id, user_id)
        return [c.to_dict() for c in vset.get_all_cards()]

    @staticmethod
    def update_card_performance(set_id: str, card_front: str, quality: int, user_id: str) -> Dict:
        db = get_db()
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
        
        next_review = datetime.now() + timedelta(days=interval_days)
        
        # Update in Firestore
        db.collection('cards').document(card.id).update({
            'level': new_level,
            'next_review': next_review
        })
        
        # Update set updated_at
        db.collection('sets').document(set_id).update({'updated_at': datetime.now()})
        
        card.level = new_level
        card.next_review = next_review
        
        return {
            'status': 'success',
            'card': card.to_dict(),
            'old_level': current_level,
            'new_level': new_level,
            'interval_days': interval_days
        }

    @staticmethod
    def delete_card(set_id: str, card_id: str, user_id: str) -> None:
        db = get_db()
        vset = VocabService.get_vocab_set(set_id, user_id) # checks access
        
        card_doc = db.collection('cards').document(str(card_id)).get()
        if not card_doc.exists:
            raise ValueError("Card not found")
            
        if card_doc.to_dict().get('vocab_set_id') != set_id:
             raise ValueError("Card not in this set")
             
        db.collection('cards').document(str(card_id)).delete()
        db.collection('sets').document(set_id).update({'updated_at': datetime.now()})

    @staticmethod
    def rename_set(set_id: str, new_name: str, user_id: str) -> VocabSet:
        db = get_db()
        vset = VocabService.get_vocab_set(set_id, user_id)
        
        if vset.user_id != user_id:
            raise ValueError("Access denied")
            
        validate_set_name(new_name)
        
        db.collection('sets').document(set_id).update({
            'name': new_name,
            'updated_at': datetime.now()
        })
        vset.name = new_name
        return vset

    @staticmethod
    def create_user_set(user_id: str, set_name: str) -> VocabSet:
        db = get_db()
        set_name = validate_set_name(set_name)
        
        # Check existing
        docs = list(db.collection('sets').where('name', '==', set_name)\
                    .where('user_id', '==', user_id).limit(1).stream())
        if docs:
            from app.utils.exceptions import InvalidInputError
            raise InvalidInputError("set_name", "Set exists")
            
        vset = VocabSet(
            name=set_name,
            user_id=user_id,
            is_shared=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        _, ref = db.collection('sets').add(vset.to_dict())
        vset.id = ref.id
        return vset

    @staticmethod
    def add_card(set_id: str, front: str, back: str, user_id: str) -> Card:
        db = get_db()
        front = validate_card_front(front)
        
        vset = VocabService.get_vocab_set(set_id, user_id)
        if vset.find_card(front):
             from app.utils.exceptions import InvalidInputError
             raise InvalidInputError("front", "Card exists")
             
        card = Card(
            vocab_set_id=set_id,
            front=front,
            back=back,
            level=1,
            next_review=datetime.now(timezone.utc)
        )
        _, ref = db.collection('cards').add(card.to_dict())
        card.id = ref.id
        
        db.collection('sets').document(set_id).update({'updated_at': datetime.now(timezone.utc)})
        return card

    @staticmethod
    def delete_set(set_id: str, user_id: str) -> Dict:
        db = get_db()
        vset = VocabService.get_vocab_set(set_id, user_id)
        
        if not vset.is_shared and vset.user_id != user_id:
            raise UnauthorizedAccessError("vocabulary set", set_id)
            
        # Delete all cards
        cards = db.collection('cards').where('vocab_set_id', '==', set_id).stream()
        batch = db.batch()
        count = 0
        for c in cards:
            batch.delete(c.reference)
            count += 1
            if count >= 400:
                batch.commit()
                batch = db.batch()
                count = 0
        if count > 0:
            batch.commit()
            
        # Delete set
        db.collection('sets').document(set_id).delete()
        
        return {'status': 'success'}

    @staticmethod
    def get_statistics(set_id: str, user_id: str) -> Dict:
        """Get statistics for a vocabulary set."""
        vset = VocabService.get_vocab_set(set_id, user_id)
        return vset.get_statistics()

    @staticmethod
    def reset_set(set_id: str, user_id: str) -> Dict:
        """Reset all cards in a set to level 1."""
        db = get_db()
        vset = VocabService.get_vocab_set(set_id, user_id)
        
        # Reset all cards to level 1
        cards = db.collection('cards').where('vocab_set_id', '==', set_id).stream()
        batch = db.batch()
        count = 0
        
        for card_doc in cards:
            batch.update(card_doc.reference, {
                'level': 1,
                'next_review': datetime.now(timezone.utc)
            })
            count += 1
            if count >= 400:
                batch.commit()
                batch = db.batch()
                count = 0
        
        if count > 0:
            batch.commit()
        
        # Update set timestamp
        db.collection('sets').document(set_id).update({'updated_at': datetime.now()})
        
        return {'status': 'success', 'message': f'Reset {count} cards to level 1'}

    @staticmethod
    def restore_card(set_id: str, card_front: str, level: int, next_review: str, user_id: str) -> Dict:
        """Restore a card to a previous state (for undo functionality)."""
        db = get_db()
        card_front = validate_card_front(card_front)
        
        vset = VocabService.get_vocab_set(set_id, user_id)
        card = vset.find_card(card_front)
        
        if not card:
            raise CardNotFoundError(card_front, vset.name)
        
        # Parse next_review from ISO format
        if isinstance(next_review, str):
            # Handle ISO format string
            next_review_date = datetime.fromisoformat(next_review.replace('Z', '+00:00'))
        else:
            next_review_date = next_review

        
        # Update card
        db.collection('cards').document(card.id).update({
            'level': level,
            'next_review': next_review_date
        })
        
        # Update set timestamp
        db.collection('sets').document(set_id).update({'updated_at': datetime.now()})
        
        card.level = level
        card.next_review = next_review_date
        
        return {
            'status': 'success',
            'card': card.to_dict()
        }
