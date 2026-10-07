import uuid

from flask_login import UserMixin
from sqlalchemy import Index, func

from app.database import db
from app.utils.time import utc_now

class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    neon_auth_id = db.Column(db.String(36), unique=True, nullable=True)
    google_sub = db.Column(db.String(255), unique=True, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    avatar_file = db.Column(db.Text, nullable=True) # Store as Base64 string for now to match previous logic

    __table_args__ = (
        Index('uq_users_username_lower', func.lower(username), unique=True),
        Index('uq_users_email_lower', func.lower(email), unique=True),
    )

    # Relationships
    sets = db.relationship('VocabSet', backref='owner', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'
