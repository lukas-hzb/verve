from datetime import datetime
from flask_login import UserMixin

from app.database import db

class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True)  # UUID
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    avatar_file = db.Column(db.Text, nullable=True) # Store as Base64 string for now to match previous logic

    # Authentication is now handled by Supabase
    # The 'id' column should match Supabase Auth User ID (UUID)
    
    # Relationships
    sets = db.relationship('VocabSet', backref='owner', lazy='dynamic', cascade='all, delete-orphan')

    # Remove set_password and check_password as we delegate to Supabase
    @property
    def is_supabase_user(self):
        return True

    def __repr__(self):
        return f'<User {self.username}>'
