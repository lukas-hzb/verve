"""
User model for authentication and user management.
Adapted for Firestore.
"""

from datetime import datetime
from flask_login import UserMixin
import bcrypt

class User(UserMixin):
    """User model for authentication."""
    
    def __init__(self, id=None, username=None, email=None, password_hash=None, created_at=None, avatar_file=None):
        self.id = id  # String ID from Firestore
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at or datetime.now()
        self.avatar_file = avatar_file
        
    def to_dict(self):
        """Convert to dictionary for Firestore."""
        return {
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'created_at': self.created_at,
            'avatar_file': self.avatar_file
        }

    @staticmethod
    def from_dict(id, data):
        """Create User from Firestore document."""
        if not data:
            return None
        return User(
            id=id,
            username=data.get('username'),
            email=data.get('email'),
            password_hash=data.get('password_hash'),
            created_at=data.get('created_at'),
            avatar_file=data.get('avatar_file')
        )
    
    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        if not self.password_hash:
            return False
        password_bytes = password.encode('utf-8')
        hash_bytes = self.password_hash.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    
    def __repr__(self):
        return f'<User {self.username}>'
