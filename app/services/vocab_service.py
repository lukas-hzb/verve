"""
Vocabulary Service - Business Logic Layer.

This module provides the business logic for managing vocabulary sets,
updating cards based on user performance, and generating statistics.
Now updated to work with SQLAlchemy database and user context.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import or_

from app.database import db
from app.models import VocabSet, Card
from app.services.sm2_algorithm import calculate_next_review, get_initial_interval_for_level
from app.utils.validators import validate_set_name, validate_quality_score, validate_card_front, validate_set_ownership
from app.utils.exceptions import VocabSetNotFoundError, CardNotFoundError, UnauthorizedAccessError


class VocabService:
    """Service class for vocabulary set operations."""
    
    @staticmethod
    def get_all_set_names(user_id: int) -> List[Dict]:
        """
        Get all vocabulary sets accessible by a user (their own + shared sets).
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of dictionaries with set information
        """
        # Get only user's own sets (not shared template sets)
        vocab_sets = VocabSet.query.filter(VocabSet.user_id == user_id).all()
        
        result = []
        for vs in vocab_sets:
            level_counts = vs.get_statistics()['level_counts']
            # Find the level with the most cards
            max_level = max(level_counts.items(), key=lambda x: x[1])[0] if level_counts else 1
            
            result.append({
                'id': vs.id,
                'name': vs.name,
                'is_shared': vs.is_shared,
                'card_count': len(vs.cards),
                'due_count': len(vs.get_due_cards()),
                'level_counts': level_counts,
                'max_level': max_level
            })
        
        return result
    
    @staticmethod
    def get_vocab_set(set_id: int, user_id: int) -> VocabSet:
        """
        Load a vocabulary set by ID with access control.
        
        Args:
            set_id: ID of the vocabulary set
            user_id: The user's ID
            
        Returns:
            VocabSet object
            
        Raises:
            VocabSetNotFoundError: If the set doesn't exist
            UnauthorizedAccessError: If user doesn't have access
        """
        vocab_set = VocabSet.query.get(set_id)
        
        if not vocab_set:
            raise VocabSetNotFoundError(f"Set ID {set_id}")
        
        # Check access rights
        validate_set_ownership(user_id, vocab_set)
        
        return vocab_set
    
    @staticmethod
    def get_vocab_set_by_name(set_name: str, user_id: int) -> Optional[VocabSet]:
        """
        Load a vocabulary set by name with access control.
        
        Args:
            set_name: Name of the vocabulary set
            user_id: The user's ID
            
        Returns:
            VocabSet object or None
        """
        set_name = validate_set_name(set_name)
        
        # Try to find user's own set first, then shared set
        vocab_set = VocabSet.query.filter(
            VocabSet.name == set_name,
            or_(VocabSet.user_id == user_id, VocabSet.is_shared == True)
        ).first()
        
        return vocab_set
    
    @staticmethod
    def get_due_cards(set_id: int, user_id: int) -> List[Dict]:
        """
        Get all cards that are due for review.
        
        Args:
            set_id: ID of the vocabulary set
            user_id: The user's ID
            
        Returns:
            List of card dictionaries
        """
        vocab_set = VocabService.get_vocab_set(set_id, user_id)
        due_cards = vocab_set.get_due_cards()
        return [card.to_dict() for card in due_cards]
    
    @staticmethod
    def get_all_cards(set_id: int, user_id: int) -> List[Dict]:
        """
        Get all cards in a vocabulary set.
        
        Args:
            set_id: ID of the vocabulary set
            user_id: The user's ID
            
        Returns:
            List of card dictionaries
        """
        vocab_set = VocabService.get_vocab_set(set_id, user_id)
        all_cards = vocab_set.get_all_cards()
        return [card.to_dict() for card in all_cards]
    
    @staticmethod
    def update_card_performance(
        set_id: int,
        card_front: str,
        quality: int,
        user_id: int
    ) -> Dict:
        """
        Update a card based on user performance using SM2 algorithm.
        
        Args:
            set_id: ID of the vocabulary set
            card_front: Front text of the card
            quality: Quality score (0-5)
            user_id: The user's ID
            
        Returns:
            Dictionary with status and updated card information
        """
        # Validate inputs
        card_front = validate_card_front(card_front)
        quality = validate_quality_score(quality)
        
        # Load vocab set and find card
        vocab_set = VocabService.get_vocab_set(set_id, user_id)
        card = vocab_set.find_card(card_front)
        
        if card is None:
            raise CardNotFoundError(card_front, vocab_set.name)
        
        # Calculate next review using SM2 algorithm
        current_level = card.level
        last_interval = get_initial_interval_for_level(current_level)
        ease_factor = 2.5
        
        new_level, interval_days, new_ease_factor = calculate_next_review(
            quality=quality,
            level=current_level,
            last_interval=last_interval,
            ease_factor=ease_factor
        )
        
        # Update card
        next_review = datetime.now() + timedelta(days=interval_days)
        vocab_set.update_card(card_front, new_level, next_review)
        
        return {
            'status': 'success',
            'card': card.to_dict(),
            'old_level': current_level,
            'new_level': new_level,
            'interval_days': interval_days
        }
    
    @staticmethod
    def restore_card(
        set_id: int,
        card_front: str,
        level: int,
        next_review: str,
        user_id: int
    ) -> Dict:
        """
        Restore a card to a previous state (undo operation).
        
        Args:
            set_id: ID of the vocabulary set
            card_front: Front text of the card
            level: Level to restore
            next_review: Next review date to restore
            user_id: The user's ID
            
        Returns:
            Dictionary with status information
        """
        # Validate inputs
        card_front = validate_card_front(card_front)
        
        # Parse next_review date
        if isinstance(next_review, str):
            try:
                next_review_dt = datetime.fromisoformat(next_review.replace('Z', '+00:00'))
            except ValueError:
                import pandas as pd
                next_review_dt = pd.to_datetime(next_review)
        else:
            next_review_dt = next_review
        
        # Load vocab set and update card
        vocab_set = VocabService.get_vocab_set(set_id, user_id)
        vocab_set.update_card(card_front, level, next_review_dt)
        
        return {'status': 'success'}
    
    @staticmethod
    def delete_card(set_id: int, card_id: int, user_id: int) -> None:
        """
        Delete a card from a vocabulary set.
        
        Args:
            set_id: ID of the vocabulary set
            card_id: ID of the card to delete
            user_id: ID of the user requesting deletion
            
        Raises:
            ValueError: If set or card not found, or access denied
        """
        vocab_set = VocabService.get_vocab_set(set_id, user_id)
        
        # Allow deletion from shared sets or owned sets
        # No ownership check needed - users can delete cards from any set they have access to
            
        card = Card.query.get(card_id)
        if not card or card.vocab_set_id != set_id:
            raise ValueError("Card not found in this set")
            
        db.session.delete(card)
        vocab_set.updated_at = datetime.now()
        db.session.commit()

    @staticmethod
    def rename_set(set_id: int, new_name: str, user_id: int) -> VocabSet:
        """
        Rename a vocabulary set.
        
        Args:
            set_id: ID of the vocabulary set
            new_name: New name for the set
            user_id: ID of the user requesting rename
            
        Returns:
            Updated VocabSet instance
            
        Raises:
            ValueError: If set not found, access denied, or invalid name
        """
        vocab_set = VocabService.get_vocab_set(set_id, user_id)
        
        # Check ownership
        if vocab_set.user_id != user_id:
            raise ValueError("Access denied: You can only rename your own sets")
            
        # Validate name
        from app.utils.validators import validate_set_name
        validate_set_name(new_name)
        
        vocab_set.name = new_name
        vocab_set.updated_at = datetime.now()
        db.session.commit()
        
        return vocab_set
    
    @staticmethod
    def reset_set(set_id: int, user_id: int) -> Dict:
        """
        Reset all cards in a set to level 1.
        
        Args:
            set_id: ID of the vocabulary set
            user_id: The user's ID
            
        Returns:
            Dictionary with status information
        """
        vocab_set = VocabService.get_vocab_set(set_id, user_id)
        
        # Don't allow resetting shared sets
        if vocab_set.is_shared:
            raise UnauthorizedAccessError("vocabulary set", set_id)
        
        vocab_set.reset_all_cards()
        
        return {
            'status': 'success',
            'message': f'All cards in {vocab_set.name} have been reset to level 1'
        }
    
    @staticmethod
    def get_statistics(set_id: int, user_id: int) -> Dict:
        """
        Get statistics for a vocabulary set.
        
        Args:
            set_id: ID of the vocabulary set
            user_id: The user's ID
            
        Returns:
            Dictionary with statistics
        """
        vocab_set = VocabService.get_vocab_set(set_id, user_id)
        return vocab_set.get_statistics()
    
    @staticmethod
    def create_user_set(user_id: int, set_name: str) -> VocabSet:
        """
        Create a new vocabulary set for a user.
        
        Args:
            user_id: The user's ID
            set_name: Name for the new set
            
        Returns:
            Created VocabSet instance
        """
        set_name = validate_set_name(set_name)
        
        # Check if user already has a set with this name
        existing = VocabSet.query.filter_by(
            name=set_name,
            user_id=user_id
        ).first()
        
        if existing:
            from app.utils.exceptions import InvalidInputError
            raise InvalidInputError("set_name", f"You already have a set named '{set_name}'")
        
        # Ensure the name does not clash with an existing shared default set
        from app.utils.exceptions import InvalidInputError
        shared_conflict = VocabSet.query.filter_by(name=set_name, is_shared=True).first()
        if shared_conflict:
            raise InvalidInputError('name', f"A shared set with the name '{set_name}' already exists. Please choose a different name.")

        vocab_set = VocabSet(
            name=set_name,
            user_id=user_id,
            is_shared=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.session.add(vocab_set)
        db.session.commit()
        
        return vocab_set
    
    @staticmethod
    def add_card(set_id: int, front: str, back: str, user_id: int) -> Card:
        """
        Add a new card to a vocabulary set.
        
        Args:
            set_id: ID of the vocabulary set
            front: Front text
            back: Back text
            user_id: The user's ID
            
        Returns:
            Created Card instance
        """
        # Validate inputs
        front = validate_card_front(front)
        if not back or not back.strip():
             from app.utils.exceptions import InvalidInputError
             raise InvalidInputError("back", "Card back cannot be empty")
             
        vocab_set = VocabService.get_vocab_set(set_id, user_id)
        
        # Check if card already exists
        if vocab_set.find_card(front):
             from app.utils.exceptions import InvalidInputError
             raise InvalidInputError("front", f"Card with front '{front}' already exists in this set")
        
        card = Card(
            vocab_set_id=set_id,
            front=front,
            back=back,
            level=1,
            next_review=datetime.now()
        )
        
        db.session.add(card)
        vocab_set.updated_at = datetime.now()
        db.session.commit()
        
        return card
    
    @staticmethod
    def delete_set(set_id: int, user_id: int) -> Dict:
        """
        Delete a vocabulary set (only if user owns it).
        
        Args:
            set_id: ID of the vocabulary set
            user_id: The user's ID
            
        Returns:
            Dictionary with status information
        """
        vocab_set = VocabService.get_vocab_set(set_id, user_id)
        
        # Don't allow deleting other users' sets
        # If it is a shared set (user_id is None), we allow deletion by any user for now
        # as per requirement to "delete example sets"
        # Don't allow deleting other users' sets unless it's a shared set
        if not vocab_set.is_shared and vocab_set.user_id != user_id:
            raise UnauthorizedAccessError("vocabulary set", set_id)
        
        set_name = vocab_set.name
        db.session.delete(vocab_set)
        db.session.commit()
        
        return {
            'status': 'success',
            'message': f"Set '{set_name}' has been deleted"
        }
