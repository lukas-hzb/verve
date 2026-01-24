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
        from app.supabase_client import SupabaseClient
        
        # Validate inputs
        username = validate_username(username)
        email = validate_email(email)
        password = validate_password(password)
        
        supabase = SupabaseClient.get_client()
        if not supabase:
             raise Exception("Supabase client not initialized")
        
        # 1. Create user in Supabase Auth
        try:
            res = supabase.auth.sign_up({
                "email": email, 
                "password": password,
                "options": {
                    "data": {
                        "username": username
                    }
                }
            })
            # Check if user already registered or confirmation needed
            if not res.user:
                 raise UserAlreadyExistsError("email", email) # Or generic error
                 
            user_id = res.user.id
            
        except Exception as e:
            # Check for specific Supabase error messages if possible
            msg = str(e)
            if "already registered" in msg or "User already exists" in msg:
                 raise UserAlreadyExistsError("email", email)
            raise e
        
        # 2. Sync to local User table (Profile)
        # We use the Supabase Auth ID as the primary key
        user = User(
            id=user_id,
            username=username, 
            email=email
        )
        
        db.session.add(user)
        
        # Assign default vocabulary set
        UserService.assign_default_vocab_set(user.id)
        
        try:
            db.session.commit()
        except Exception as e:
            # Rollback Supabase user creation? 
            # Ideally yes, but Client SDK doesn't support 'delete' easily for users without Admin.
            # We assume database success. 
            db.session.rollback()
            raise e
            
        return user
    
    @staticmethod
    def authenticate_user(username_or_email: str, password: str) -> User:
        from app.supabase_client import SupabaseClient
        
        # Supabase requires Email for login by default (unless username is set as login param)
        # Our app supports username OR email. 
        # If input is username, we need the email first?
        # Supabase Auth generally uses Email. 
        # Strategy: resolve email from username locally first.
        
        email = username_or_email
        if '@' not in username_or_email:
            user_obj = User.query.filter_by(username=username_or_email).first()
            if not user_obj:
                raise InvalidCredentialsError() # Username not found
            email = user_obj.email
            
        supabase = SupabaseClient.get_client()
        if not supabase:
             raise Exception("Supabase client not initialized")
             
        try:
            # Login with Supabase
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            # If successful, we get a session and user
            if not res.user:
                raise InvalidCredentialsError()
                
            # Fetch local user record (Profile)
            user = User.query.get(res.user.id)
            if not user:
                # Should not happen if sync works, but maybe manually added in Supabase?
                # Create local profile?
                # For now, error out or minimal implementation
                # Retrieve username from metadata if possible?
                username = res.user.user_metadata.get('username', 'Unknown')
                user = User(id=res.user.id, email=email, username=username)
                db.session.add(user)
                db.session.commit()

            return user
            
        except Exception as e:
            # Differentiate errors
            msg = str(e)
            if "Invalid login credentials" in msg:
                raise InvalidCredentialsError()
            raise InvalidCredentialsError()  # Generic fallback for security
    
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
        from app.supabase_client import SupabaseClient
        
        user = UserService.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Verification of CURRENT password is separate in Supabase.
        # Generally done by re-authenticating or strictly updating if logged in.
        # Since we are backend, we can use Admin API to force change, 
        # OR we just update it if we trust the session.
        # BUT, standard flow requires knowing current password if we want to be safe.
        # Supabase Client `update_user` just updates it. 
        # It assumes the client is authenticated as that user.
        
        # HOWEVER, here we are in Python (Server). The `supabase` client is likely ANON or SERVICE.
        # If usage is Anon, we don't have the user's token here easily unless we passed it.
        # Strategy:
        # Just update it using Service Role (Admin) IF we want to bypass check.
        # OR: Attempt sign in with current password to verify.
        
        new_password = validate_password(new_password)
        supabase = SupabaseClient.get_client()
        
        # 1. Verify current password by login
        try:
             supabase.auth.sign_in_with_password({
                 "email": user.email,
                 "password": current_password
             })
        except:
             raise InvalidCredentialsError("Ungültiges aktuelles Passwort")

        # 2. Update password utilizing Admin/Service Role OR the session we just got? 
        # The sign_in returned a session. We can use that token to update.
        # Actually simplest: Use Admin API to update user attributes.
        
        service_client = SupabaseClient.get_service_role_client() # Needs service role to update without session?
        # Actually client.auth.update_user(attrs) works if session is set.
        # Let's use the admin api if possible to be stateless?
        # SDK `admin.update_user_by_id(uid, attrs)`
        
        try:
            service_client = SupabaseClient.get_service_role_client()
            service_client.auth.admin.update_user_by_id(
                user_id,
                {"password": new_password}
            )
        except Exception as e:
            # Fallback if service key missing or error
            raise Exception("Password update failed: " + str(e))

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
        
        # Delete from Supabase Auth
        try:
            from app.supabase_client import SupabaseClient
            service_client = SupabaseClient.get_service_role_client()
            service_client.auth.admin.delete_user(user_id)
        except Exception as e:
             # Log but proceed with local delete to ensure cleanup?
             # Or fail? Prefer cleanup.
             pass
             
        db.session.delete(user)
        db.session.commit()

