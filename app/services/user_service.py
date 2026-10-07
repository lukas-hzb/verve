"""
User Service - Business Logic for User Management.
Adapted for SQLAlchemy.
"""

import re
import uuid
from typing import Optional
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from app.database import db
from app.models import User, VocabSet, Card
from app.services.avatar_service import AvatarService
from app.utils.time import utc_now
from app.utils.validators import validate_username, validate_email
from app.utils.exceptions import UserAlreadyExistsError

class UserService:
    """Service class for user management operations."""
    
    @staticmethod
    def resolve_neon_user(identity: dict) -> User:
        """Bind a server-validated Neon identity without replacing application IDs."""
        from app.utils.exceptions import InvalidCredentialsError
        neon_id = str(uuid.UUID(identity['id']))
        user = User.query.filter_by(neon_auth_id=neon_id).first()
        if user:
            return user

        email = validate_email(identity['email'])
        # Google subject IDs are stable across OAuth clients. Read only the identity
        # link, never Google's access/refresh tokens, from the managed schema.
        google_sub = UserService.google_subject(neon_id)
        if google_sub:
            user = User.query.filter_by(google_sub=google_sub).first()
        if not user and identity.get('emailVerified') is True:
            user = User.query.filter(func.lower(User.email) == email.lower()).first()
            if user and user.google_sub and user.google_sub != google_sub:
                raise InvalidCredentialsError()
        if user:
            if user.neon_auth_id and user.neon_auth_id != neon_id:
                raise InvalidCredentialsError()
            user.neon_auth_id = neon_id
        else:
            # Unverified email must never claim an existing account.
            if User.query.filter(func.lower(User.email) == email.lower()).first():
                raise InvalidCredentialsError('Verify your email before accessing your existing account.')
            base = re.sub(r'[^a-zA-Z0-9_]', '', identity.get('name') or '')[:50]
            if len(base) < 3:
                base = f'user_{uuid.uuid4().hex[:8]}'
            username, counter = base, 1
            while User.query.filter(func.lower(User.username) == username.lower()).first():
                suffix = f'_{counter}'
                username = f'{base[:50-len(suffix)]}{suffix}'
                counter += 1
            user = User(id=str(uuid.uuid4()), username=username, email=email,
                        neon_auth_id=neon_id, google_sub=google_sub)
            db.session.add(user)
            db.session.flush()
            UserService.assign_default_vocab_set(user.id)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return user

    @staticmethod
    def google_subject(neon_id: str) -> str | None:
        return db.session.execute(text(
            'SELECT "accountId" FROM neon_auth.account '
            'WHERE "userId" = CAST(:id AS uuid) AND "providerId" = \'google\''
        ), {'id': neon_id}).scalar()

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
        # Email belongs to the managed identity and cannot be changed locally.
        email = user.email
        
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
    def delete_managed_identity(neon_id: str) -> None:
        # Managed sessions and provider accounts cascade from this identity.
        # Use the same PostgreSQL transaction as the application data deletion.
        result = db.session.execute(text(
            'DELETE FROM neon_auth."user" WHERE id = CAST(:id AS uuid)'
        ), {'id': str(uuid.UUID(neon_id))})
        if result.rowcount != 1:
            raise ValueError('Managed identity no longer exists')

    @staticmethod
    def delete_user(user_id: str) -> None:
        user = UserService.get_user_by_id(user_id)
        if not user or not user.neon_auth_id:
            raise ValueError('Linked managed identity required')
        try:
            UserService.delete_managed_identity(user.neon_auth_id)
            db.session.delete(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
