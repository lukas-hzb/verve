"""
User Service - Business Logic for User Management.
Adapted for SQLAlchemy.
"""

import uuid
from typing import Optional
from app.database import db
from app.models import User, VocabSet, Card
from app.utils.validators import validate_username, validate_email, validate_password
from app.utils.exceptions import UserAlreadyExistsError, InvalidCredentialsError, InvalidInputError

class UserService:
    """Service class for user management operations."""
    
    @staticmethod
    def create_user(username: str, email: str, password: str) -> User:
        # Validate inputs
        username = validate_username(username)
        email = validate_email(email)
        password = validate_password(password)
        
        # Check if username exists
        if User.query.filter_by(username=username).first():
            raise UserAlreadyExistsError("username", username)
        
        # Check if email exists
        if User.query.filter_by(email=email).first():
            raise UserAlreadyExistsError("email", email)
        
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            username=username, 
            email=email
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Assign default vocabulary set
        UserService.assign_default_vocab_set(user.id)
        
        return user
    
    @staticmethod
    def authenticate_user(username_or_email: str, password: str) -> User:
        # Try to find user by username
        user = User.query.filter_by(username=username_or_email).first()
        if not user:
            # Try by email
            user = User.query.filter_by(email=username_or_email).first()
            
        if not user:
            raise InvalidCredentialsError()
            
        if not user.check_password(password):
            raise InvalidCredentialsError()
        
        return user
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[User]:
        return User.query.get(user_id)
    
    @staticmethod
    def assign_default_vocab_set(user_id: str) -> None:
        from datetime import datetime
        
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
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(user_set)
        
        # Copy cards
        # We process efficiently by querying and bulk inserting if possible, 
        # but standard add loop is fine for this scale
        
        # Set next_review to past so cards are immediately due
        # Use timezone naive or UTC as appropriate. Models default to utcnow.
        from datetime import timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        for card in default_set.cards:
            new_card = Card(
                id=str(uuid.uuid4()),
                vocab_set_id=new_set_id,
                front=card.front,
                back=card.back,
                level=1,
                next_review=yesterday
            )
            db.session.add(new_card)
        
        db.session.commit()

    @staticmethod
    def update_user_profile(user_id: str, username: str, email: str, avatar_file=None, remove_avatar=False) -> User:
        import os
        from werkzeug.utils import secure_filename
        
        user = UserService.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
            
        username = validate_username(username)
        email = validate_email(email)
        
        # Check unique username
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user_id:
            raise UserAlreadyExistsError("username", username)

        # Check unique email
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != user_id:
             raise UserAlreadyExistsError("email", email)
            
        user.username = username
        user.email = email
        
        if remove_avatar:
            user.avatar_file = None
        elif avatar_file and avatar_file.filename:
            filename = secure_filename(avatar_file.filename)
            file_ext = os.path.splitext(filename)[1]
            if file_ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif']:
                 raise InvalidInputError("avatar", "Invalid file type")
                 
            # Process image with Pillow
            import base64
            import io
            from PIL import Image
            
            # Open image
            img = Image.open(avatar_file)
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
                
            # Resize
            img.thumbnail((150, 150))
            
            # Save to buffer
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=70)
            buffer.seek(0)
            
            # Encode
            img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            user.avatar_file = f"data:image/jpeg;base64,{img_str}"
        
        db.session.commit()
        return user

    @staticmethod
    def change_password(user_id: str, current_password: str, new_password: str) -> None:
        user = UserService.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
            
        if not user.check_password(current_password):
            raise InvalidCredentialsError("Ungültiges aktuelles Passwort")
            
        new_password = validate_password(new_password)
        user.set_password(new_password)
        db.session.commit()

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
        db.session.commit()

