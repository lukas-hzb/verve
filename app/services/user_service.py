"""
User Service - Business Logic for User Management.
Adapted for SQLAlchemy.
"""

import re
import uuid
from typing import Optional
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.database import db
from app.models import User, VocabSet, Card
from app.services.avatar_service import AvatarService
from app.utils.time import utc_now
from app.utils.validators import validate_username, validate_email, validate_password
from app.utils.exceptions import UserAlreadyExistsError, InvalidCredentialsError

class UserService:
    """Service class for user management operations."""
    
    @staticmethod
    def create_user(username: str, email: str, password: str) -> User:
        """Create a local account whose credentials live in PostgreSQL."""
        username = validate_username(username)
        email = validate_email(email)
        password = validate_password(password)

        if User.query.filter(func.lower(User.email) == email.lower()).first():
            raise UserAlreadyExistsError("email", email)
        if User.query.filter(func.lower(User.username) == username.lower()).first():
            raise UserAlreadyExistsError("username", username)

        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
        )
        user.set_password(password)
        db.session.add(user)

        try:
            db.session.flush()
            UserService.assign_default_vocab_set(user.id)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            UserService._raise_duplicate_user(username, email)
            raise
        except Exception:
            db.session.rollback()
            raise

        return user
    
    @staticmethod
    def authenticate_user(username_or_email: str, password: str) -> User:
        """Authenticate an account without disclosing which field was incorrect."""
        identifier = (username_or_email or '').strip()
        if '@' not in identifier:
            user = User.query.filter(func.lower(User.username) == identifier.lower()).first()
        else:
            email = identifier.lower()
            user = User.query.filter(func.lower(User.email) == email).first()

        if not user:
            User.check_dummy_password(password or '')
            raise InvalidCredentialsError()
        if not user.check_password(password):
            raise InvalidCredentialsError()

        # Transparently upgrade imported Supabase bcrypt hashes to scrypt.
        if user.has_legacy_password_hash:
            user.set_password(password)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

        return user

    @staticmethod
    def get_or_create_google_user(google_sub: str, email: str, suggested_username: str) -> User:
        """Resolve a verified Google identity and safely link it by email once."""
        email = validate_email(email)
        google_sub = str(google_sub).strip()
        if not google_sub:
            raise InvalidCredentialsError()

        user = User.query.filter_by(google_sub=google_sub).first()
        if user:
            return user

        user = User.query.filter(func.lower(User.email) == email).first()
        if user:
            if user.google_sub and user.google_sub != google_sub:
                raise InvalidCredentialsError()
            user.google_sub = google_sub
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
            return user

        base_username = re.sub(r'[^a-zA-Z0-9_]', '', suggested_username or '')
        if len(base_username) < 3:
            base_username = f"user_{uuid.uuid4().hex[:8]}"
        base_username = base_username[:50]

        username = base_username
        counter = 1
        while User.query.filter(func.lower(User.username) == username.lower()).first():
            suffix = f"_{counter}"
            username = f"{base_username[:50 - len(suffix)]}{suffix}"
            counter += 1

        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            google_sub=google_sub,
        )
        db.session.add(user)

        try:
            db.session.flush()
            UserService.assign_default_vocab_set(user.id)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            UserService._raise_duplicate_user(username, email)
            raise
        except Exception:
            db.session.rollback()
            raise

        return user
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[User]:
        return db.session.get(User, user_id)

    @staticmethod
    def _raise_duplicate_user(username: str, email: str) -> None:
        """Translate database uniqueness failures into stable domain errors."""
        if User.query.filter(func.lower(User.email) == email.lower()).first():
            raise UserAlreadyExistsError('email', email)
        if User.query.filter(func.lower(User.username) == username.lower()).first():
            raise UserAlreadyExistsError('username', username)
    
    @staticmethod
    def assign_default_vocab_set(user_id: str) -> None:
        # Check if user already has the default set
        existing_set = VocabSet.query.filter_by(user_id=user_id, name="Hauptstädte", is_shared=False).first()
        if existing_set:
            return
        
        # Get the shared default set
        default_set = VocabSet.query.filter_by(is_shared=True, name="Hauptstädte").first()
        if not default_set:
            return
            
        # Create user set
        new_set_id = str(uuid.uuid4())
        user_set = VocabSet(
            id=new_set_id,
            name="Hauptstädte",
            user_id=user_id,
            is_shared=False,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.session.add(user_set)
        
        # Copy cards
        # We process efficiently by querying and bulk inserting if possible, 
        # but standard add loop is fine for this scale
        
        # Set next_review to past so cards are immediately due
        # Use timezone naive or UTC as appropriate. Models default to utcnow.
        from datetime import timedelta
        yesterday = utc_now() - timedelta(days=1)

        cards = [
            Card(
                id=str(uuid.uuid4()),
                vocab_set_id=new_set_id,
                front=card.front,
                back=card.back,
                level=1,
                next_review=yesterday
            )
            for card in default_set.cards
        ]
        db.session.add_all(cards)

    @staticmethod
    def update_user_profile(user_id: str, username: str, email: str, avatar_file=None, remove_avatar=False) -> User:
        user = UserService.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
            
        username = validate_username(username)
        email = validate_email(email)
        
        # Check unique username
        existing_user = User.query.filter(func.lower(User.username) == username.lower()).first()
        if existing_user and existing_user.id != user_id:
            raise UserAlreadyExistsError("username", username)

        # Check unique email
        existing_email = User.query.filter(func.lower(User.email) == email.lower()).first()
        if existing_email and existing_email.id != user_id:
             raise UserAlreadyExistsError("email", email)
            
        user.username = username
        user.email = email
        
        if remove_avatar:
            user.avatar_file = None
        elif avatar_file and avatar_file.filename:
            user.avatar_file = AvatarService.process(avatar_file)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            UserService._raise_duplicate_user(username, email)
            raise
        except Exception:
            db.session.rollback()
            raise
        return user

    @staticmethod
    def change_password(user_id: str, current_password: str, new_password: str) -> None:
        user = UserService.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        new_password = validate_password(new_password)

        if not user.password_hash or not user.check_password(current_password):
            raise InvalidCredentialsError("Ungültiges aktuelles Passwort")

        user.set_password(new_password)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def delete_user(user_id: str) -> None:
        """
        Permanently delete a user and all associated data.
        """
        user = UserService.get_user_by_id(user_id)
        if not user:
            return
            
        # SQLAlchemy cascade='all, delete-orphan' on User.sets handles sets and cards
        # But we made Card relationship on VocabSet, and VocabSet relationship on User.
        # So deleting user deletes their sets. Deleting sets deletes their cards.
        
        db.session.delete(user)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
