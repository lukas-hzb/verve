"""
User Service - Business Logic for User Management.
Adapted for Firestore.
"""

from typing import Optional
from app.firestore_db import get_db
from app.models import User, VocabSet
from app.utils.validators import validate_username, validate_email, validate_password
from app.utils.exceptions import UserAlreadyExistsError, InvalidCredentialsError

class UserService:
    """Service class for user management operations."""
    
    @staticmethod
    def create_user(username: str, email: str, password: str) -> User:
        db = get_db()
        
        # Validate inputs
        username = validate_username(username)
        email = validate_email(email)
        password = validate_password(password)
        
        # Check if username exists
        docs = db.collection('users').where('username', '==', username).limit(1).stream()
        if any(docs):
            raise UserAlreadyExistsError("username", username)
        
        # Check if email exists
        docs = db.collection('users').where('email', '==', email).limit(1).stream()
        if any(docs):
            raise UserAlreadyExistsError("email", email)
        
        # Create user
        user = User(username=username, email=email)
        user.set_password(password)
        
        # Add to Firestore (auto-ID)
        _, doc_ref = db.collection('users').add(user.to_dict())
        user.id = doc_ref.id
        
        # Assign default vocabulary set
        UserService.assign_default_vocab_set(user.id)
        
        return user
    
    @staticmethod
    def authenticate_user(username_or_email: str, password: str) -> User:
        db = get_db()
        
        # Try to find user by username
        docs = list(db.collection('users').where('username', '==', username_or_email).limit(1).stream())
        if not docs:
            # Try by email
            docs = list(db.collection('users').where('email', '==', username_or_email).limit(1).stream())
            
        if not docs:
            raise InvalidCredentialsError()
            
        user_data = docs[0].to_dict()
        user = User.from_dict(docs[0].id, user_data)
        
        if not user.check_password(password):
            raise InvalidCredentialsError()
        
        return user
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[User]:
        db = get_db()
        doc = db.collection('users').document(str(user_id)).get()
        if not doc.exists:
            return None
        return User.from_dict(doc.id, doc.to_dict())
    
    @staticmethod
    def assign_default_vocab_set(user_id: str) -> None:
        db = get_db()
        from datetime import datetime
        from app.models import Card
        
        # Check if user already has the default set
        docs = db.collection('sets').where('user_id', '==', user_id)\
                 .where('name', '==', "Hauptstädte")\
                 .where('is_shared', '==', False).limit(1).stream()
        
        if any(docs):
            return
        
        # Get the shared default set
        docs = list(db.collection('sets').where('is_shared', '==', True)\
                    .where('name', '==', "Hauptstädte").limit(1).stream())
        
        if not docs:
            return
            
        default_set_doc = docs[0]
        
        # Create user set
        user_set = VocabSet(
            name="Hauptstädte",
            user_id=user_id,
            is_shared=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        _, set_ref = db.collection('sets').add(user_set.to_dict())
        
        # Copy cards
        # First query cards for default set
        cards_stream = db.collection('cards').where('vocab_set_id', '==', default_set_doc.id).stream()
        
        batch = db.batch()
        count = 0
        for card_doc in cards_stream:
            card_data = card_doc.to_dict()
            new_card = Card(
                vocab_set_id=set_ref.id,
                front=card_data.get('front'),
                back=card_data.get('back'),
                level=1,
                next_review=datetime.now()
            )
            new_card_ref = db.collection('cards').document()
            batch.set(new_card_ref, new_card.to_dict())
            count += 1
            if count >= 400:
                batch.commit()
                batch = db.batch()
                count = 0
        
        if count > 0:
            batch.commit()

    @staticmethod
    def update_user_profile(user_id: str, username: str, email: str, avatar_file=None, remove_avatar=False) -> User:
        db = get_db()
        import os
        from werkzeug.utils import secure_filename
        from flask import current_app
        
        user = UserService.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
            
        username = validate_username(username)
        email = validate_email(email)
        
        # Check unique username
        docs = list(db.collection('users').where('username', '==', username).stream())
        for d in docs:
            if d.id != user_id:
                raise UserAlreadyExistsError("username", username)

        # Check unique email
        docs = list(db.collection('users').where('email', '==', email).stream())
        for d in docs:
            if d.id != user_id:
                raise UserAlreadyExistsError("email", email)
            
        user.username = username
        user.email = email
        
        if remove_avatar:
            user.avatar_file = None
        elif avatar_file and avatar_file.filename:
            filename = secure_filename(avatar_file.filename)
            file_ext = os.path.splitext(filename)[1]
            if file_ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif']:
                 from app.utils.exceptions import InvalidInputError
                 raise InvalidInputError("avatar", "Invalid file type")
                 
            new_filename = f"avatar_{user.id}{file_ext}"
            upload_folder = current_app.config['UPLOAD_FOLDER'] / "avatars"
            upload_folder.mkdir(parents=True, exist_ok=True)
            avatar_path = upload_folder / new_filename
            avatar_file.save(str(avatar_path))
            user.avatar_file = f"uploads/avatars/{new_filename}"
        
        db.collection('users').document(user_id).set(user.to_dict(), merge=True)
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
        
        get_db().collection('users').document(user_id).update({
            'password_hash': user.password_hash
        })

    @staticmethod
    def delete_user(user_id: str) -> None:
        """
        Permanently delete a user and all associated data.
        """
        db = get_db()
        from flask import current_app
        
        user = UserService.get_user_by_id(user_id)
        if not user:
            return
            
        # 1. Delete all sets and cards
        # Get all sets for user
        sets = db.collection('sets').where('user_id', '==', user_id).stream()
        
        batch = db.batch()
        count = 0
        
        for s in sets:
            # Delete cards for this set
            cards = db.collection('cards').where('vocab_set_id', '==', s.id).stream()
            for c in cards:
                batch.delete(c.reference)
                count += 1
                if count >= 400:
                    batch.commit()
                    batch = db.batch()
                    count = 0
            
            # Delete set
            batch.delete(s.reference)
            count += 1
            if count >= 400:
                batch.commit()
                batch = db.batch()
                count = 0
                
        if count > 0:
            batch.commit()
            
        # 2. Delete avatar
        if user.avatar_file:
            try:
                avatar_path = current_app.config['UPLOAD_FOLDER'] / user.avatar_file.replace('uploads/', '')
                if avatar_path.exists():
                    avatar_path.unlink()
            except Exception as e:
                current_app.logger.error(f"Failed to delete avatar file: {e}")
                
        # 3. Delete user
        db.collection('users').document(user_id).delete()
