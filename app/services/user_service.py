"""
User Service - Business Logic for User Management.

This module provides the business logic for user authentication,
registration, and profile management.
"""

from typing import Optional
from app.database import db
from app.models import User, VocabSet
from app.utils.validators import validate_username, validate_email, validate_password
from app.utils.exceptions import UserAlreadyExistsError, InvalidCredentialsError


class UserService:
    """Service class for user management operations."""
    
    @staticmethod
    def create_user(username: str, email: str, password: str) -> User:
        """
        Create a new user account.
        
        Args:
            username: Desired username
            email: User's email address
            password: Plain text password
            
        Returns:
            Created User instance
            
        Raises:
            InvalidInputError: If any input is invalid
            UserAlreadyExistsError: If username or email already exists
        """
        # Validate inputs
        username = validate_username(username)
        email = validate_email(email)
        password = validate_password(password)
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            raise UserAlreadyExistsError("username", username)
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            raise UserAlreadyExistsError("email", email)
        
        # Create user
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Assign default vocabulary set
        UserService.assign_default_vocab_set(user.id)
        
        return user
    
    @staticmethod
    def authenticate_user(username_or_email: str, password: str) -> User:
        """
        Authenticate a user with username/email and password.
        
        Args:
            username_or_email: Username or email address
            password: Plain text password
            
        Returns:
            Authenticated User instance
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        # Try to find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        if not user or not user.check_password(password):
            raise InvalidCredentialsError()
        
        return user
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """
        Get a user by their ID.
        
        Args:
            user_id: The user's ID
            
        Returns:
            User instance or None if not found
        """
        return User.query.get(user_id)
    
    @staticmethod
    def assign_default_vocab_set(user_id: int) -> None:
        """
        Assign the default shared vocabulary set to a new user.
        This creates a user-specific copy of the shared set.
        
        Args:
            user_id: The user's ID
        """
        from datetime import datetime
        from app.models import Card
        
        # Check if user already has the default set
        existing_set = VocabSet.query.filter_by(
            user_id=user_id,
            name="Hauptstädte",
            is_shared=False
        ).first()
        
        if existing_set:
            # User already has the default set, don't create duplicates
            return
        
        # Get the shared default set
        default_set = VocabSet.query.filter_by(is_shared=True, name="Hauptstädte").first()
        
        if not default_set:
            # If no shared set exists, user will only see their own sets
            return
        
        # Create a copy of the default set for this user
        user_set = VocabSet(
            name=f"Hauptstädte",
            user_id=user_id,
            is_shared=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.session.add(user_set)
        db.session.flush()
        
        # Copy all cards from the shared set to the user's set
        # Reset progress so user starts fresh
        for card in default_set.cards:
            user_card = Card(
                vocab_set_id=user_set.id,
                front=card.front,
                back=card.back,
                level=1,
                next_review=datetime.now()
            )
            db.session.add(user_card)
        
        db.session.commit()

    @staticmethod
    def update_user_profile(user_id: int, username: str, email: str, avatar_file=None, remove_avatar=False) -> User:
        """
        Update a user's profile information.
        
        Args:
            user_id: The user's ID
            username: New username
            email: New email
            avatar_file: Optional file object for avatar
            remove_avatar: If True, remove the current avatar
            
        Returns:
            Updated User instance
            
        Raises:
            InvalidInputError: If inputs are invalid
            UserAlreadyExistsError: If username/email taken by another user
        """
        import os
        from werkzeug.utils import secure_filename
        from flask import current_app
        
        user = UserService.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
            
        # Validate inputs
        username = validate_username(username)
        email = validate_email(email)
        
        # Check if username taken by ANOTHER user
        existing_user = User.query.filter(User.username == username, User.id != user_id).first()
        if existing_user:
            raise UserAlreadyExistsError("username", username)
            
        # Check if email taken by ANOTHER user
        existing_email = User.query.filter(User.email == email, User.id != user_id).first()
        if existing_email:
            raise UserAlreadyExistsError("email", email)
            
        user.username = username
        user.email = email
        
        # Handle avatar removal
        if remove_avatar:
            user.avatar_file = None
        # Handle avatar upload
        elif avatar_file and avatar_file.filename:
            filename = secure_filename(avatar_file.filename)
            # Use user ID to make filename unique and avoid collisions
            file_ext = os.path.splitext(filename)[1]
            if file_ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif']:
                 from app.utils.exceptions import InvalidInputError
                 raise InvalidInputError("avatar", "Invalid file type. Allowed: jpg, jpeg, png, gif")
                 
            new_filename = f"avatar_{user.id}{file_ext}"
            
            # Ensure upload directory exists
            upload_folder = current_app.config['UPLOAD_FOLDER'] / "avatars"
            upload_folder.mkdir(parents=True, exist_ok=True)
            
            avatar_path = upload_folder / new_filename
            avatar_file.save(str(avatar_path))
            
            # Save RELATIVE path to DB (relative to static folder)
            user.avatar_file = f"uploads/avatars/{new_filename}"
        
        db.session.commit()
        return user

    @staticmethod
    def change_password(user_id: int, current_password: str, new_password: str) -> None:
        """
        Change a user's password.
        
        Args:
            user_id: The user's ID
            current_password: The current password
            new_password: The new password
            
        Raises:
            InvalidCredentialsError: If current password is incorrect
            InvalidInputError: If new password is invalid
        """
        user = UserService.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
            
        # Verify current password
        if not user.check_password(current_password):
            raise InvalidCredentialsError("Ungültiges aktuelles Passwort")
            
        # Validate new password
        new_password = validate_password(new_password)
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
